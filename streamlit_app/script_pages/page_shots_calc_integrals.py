import streamlit as st
import pandas as pd
import numpy as np
from glob import glob
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from datetime import datetime



st.title('Calculate integrals of shots')

st.logo(image="images/logo.png", icon_image="images/icon.png")

files = glob(os.path.join("Measurements", "Shots", "*.csv"))

# sort by date parsed from filename (assuming format YYYY-MM-DD_HH-MM-SS.csv)
def extract_datetime_from_name(path):
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    try:
        return datetime.strptime(base[-19:], "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        # fallback: find it anywhere in the name just in case
        m = re.search(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", base)
        return datetime.strptime(m.group(0), "%Y-%m-%d_%H-%M-%S") if m else datetime.min

files = sorted(files, key=extract_datetime_from_name, reverse=True)

filenames = [os.path.basename(file) for file in files]

filename = st.selectbox('Select file to calculate integrals', filenames)

@st.cache_data
def read_dataframe(file):
    #confirm the rows to skip
    file0 = open(file)
    firstlines = file0.readlines()
    file0.close()
    for line in firstlines:
        if line.startswith("ACR used:"):
            acr_used = line[11:]
    for line in firstlines:
        if line.startswith("Rank used:"):
            rank = line[11:-1]
            st.write(f'Rank uses: {rank}')
            break
    if rank == '1':
        capacitor = 10/1000
    elif rank == '2':
        capacitor = 30/1000
    elif rank == '4':
        capacitor = 60/1000
    elif rank == '8':
        capacitor = 1.8
    for line in firstlines:
        if line.startswith("Integration time:"):
            integration_time = line[18:-3]
    for n, line in enumerate(firstlines):
        if line.startswith('Number,Time'):
            lines_to_skip = n
            break
    #then read the data frame
    df = pd.read_csv(file, skiprows = lines_to_skip)
    return df, capacitor, float(integration_time)

df, capacitor, inegration_time_us = read_dataframe(os.path.join("Measurements", "Shots", filename))

cutoff = st.selectbox('cut off', [0.5, 8, 10, 20, 40, 100, 150], index = 4)

last_Time = df.iloc[-1,1]
zeros = df.loc[(df.Time < 1) | (df.Time > last_Time - 1), ['ch0', 'ch1']].mean()
dfchz = df.loc[:, ['ch0','ch1']] - zeros
dfchz.columns = ['ch0z', 'ch1z']
dfz = pd.concat([df, dfchz], axis = 1)
st.dataframe(df)

ACR = st.number_input('ACR value', value = 1.0, format = '%.2f')
calibration_factor = st.session_state.get("calibration_factor", 1.0)
st.caption(f"Calibration factor from Settings: {calibration_factor:.3f}")
dfz['sensorcharge'] = dfz.ch0z * capacitor
dfz['cerenkovcharge'] = dfz.ch1z * capacitor
dfz['dose'] = (dfz.sensorcharge - dfz.cerenkovcharge * ACR) * calibration_factor

dfz['chunk'] = dfz.Number // (300000/700)
group = dfz.groupby('chunk')
dfg = group.agg({'Time':np.median,
                'ch0z':np.sum,
                'ch1z':np.sum})
dfg['Time_min'] = group['Time'].min()
dfg['Time_max'] = group['Time'].max()
dfg['ch0diff'] = dfg.ch0z.diff()
startTimes = dfg.loc[dfg.ch0diff > cutoff, 'Time_min']
finishTimes = dfg.loc[dfg.ch0diff < -cutoff, 'Time_max']
stss = [startTimes.iloc[0]] + list(startTimes[startTimes.diff()>2])
sts = [t - 0.08 for t in stss]
ftss = [finishTimes.iloc[0]] + list(finishTimes[finishTimes.diff()>2])
fts = [t + 0.04 for t in ftss]

#Find pulses
maxvaluech = dfz.loc[(dfz.Time < sts[0] - 1) | (dfz.Time > fts[-1] + 1), 'ch0z'].max()
dfz['pulse'] = dfz.ch0z > maxvaluech * 1.05
dfz.loc[dfz.pulse, 'pulsenum'] = 1
dfz.fillna({'pulsenum':0}, inplace = True)
dfz['pulsecoincide'] = dfz.loc[dfz.pulse, 'Number'].diff() == 1
dfz.fillna({'pulsecoincide':False}, inplace = True)
dfz['singlepulse'] = dfz.pulse & ~dfz.pulsecoincide
dfz.loc[dfz.singlepulse, 'pulsetoplot'] = dfz.singlepulse * 1

#Group by 300 ms
dfz['chunk'] = dfz.Number // int(300000/750)
dfg = dfz.groupby('chunk').agg({'Time':np.median, 'ch0z':np.sum, 'ch1z':np.sum})

fig1 = go.Figure()

fig1.add_trace(go.Scatter(x=dfg.Time, y=dfg.ch0z,
                        mode='lines',
                        name='ch0z'))

fig1.add_trace(go.Scatter(x=dfg.Time, y=dfg.ch1z,
                        mode = 'lines',
                        name = 'ch1z'))

dfz['shot'] = -1


for (n, (s, f)) in enumerate(zip(sts, fts)):
    fig1.add_vline(x=s, line_color='green', opacity = 0.5, line_dash='dash')
    fig1.add_vline(x=f, line_color='red', opacity = 0.5, line_dash='dash')
    dfz.loc[(dfz.Time > s) & (dfz.Time < f), 'shot'] = n
fig1.update_xaxes(title = 'Time (s)')
fig1.update_yaxes(title = 'Voltage (V)')

st.plotly_chart(fig1)

dfi = dfz.groupby('shot').agg({'sensorcharge':np.sum,
                                'cerenkovcharge':np.sum,
                                'dose':np.sum,
                                'singlepulse':np.sum,
                               'pulsecoincide':np.sum})
dfi.reset_index(inplace = True)
dfig = dfi.loc[dfi.shot != -1, :]

st.dataframe(dfig)

#Calculate Standard Deviation
calcstd = st.checkbox('Calculate Standard Deviation')
if calcstd:
    stdnow = dfig.dose.std()/dfig.dose.mean() * 100
    st.write('Standard Deviation = %.2f %%' %stdnow)

pulseson = st.checkbox('See pulses')

if pulseson:
    dfz0 = dfz.loc[:, ['Time', 'ch0z']]
    dfz0.columns = ['Time', 'signal']
    dfz0['ch'] = 'ch0z'
    dfz1 = dfz.loc[:, ['Time', 'ch1z']]
    dfz1.columns = ['Time', 'signal']
    dfz1['ch'] = 'ch1z'
    dfztp = pd.concat([dfz0, dfz1])

    fig2 = px.line(dfztp, x='Time', y='signal', color = 'ch', markers = True)

    #fig2.add_trace(go.Scatter(x=dfz.Time, y=dfz.pulsetoplot,
    #                    mode = 'markers',
    #                    name = 'pulses'))
    fig2.update_traces(marker=dict(size=4))
    fig2.update_xaxes(title = 'Time (s)')
    fig2.update_yaxes(title = 'Voltage (V)')
    for (s, f) in zip(sts, fts):
        fig2.add_vline(x=s, line_color='green', opacity = 0.5, line_dash='dash')
        fig2.add_vline(x=f, line_color='red', opacity = 0.5, line_dash='dash')
    st.plotly_chart(fig2)
