import streamlit as st
import pandas as pd
import numpy as np
import os
import re
import plotly.express as px
import plotly.graph_objects as go
from glob import glob
from datetime import datetime

st.logo(image="images/logo.png", icon_image="images/icon.png")

st.title('Calculate ACR')

def R2(x, y, xmax=False, r2offset=0):
    coeff, cov = np.polyfit(x, y, 1, cov=True)
    stdcoeff = np.sqrt(np.diag(cov))
    polinomio = np.poly1d(coeff)
    yhat = polinomio(x)
    ybar = np.sum(y) / len(y)
    sstot = np.sum((y - ybar) ** 2)
    ssres = np.sum((y - yhat) ** 2)
    R2 = 1 - ssres / sstot
    if xmax:
        xline = np.linspace(x.min(), xmax)
    else:
        xline = np.linspace(x.min(), x.max())
    figline = go.Line(
        x=xline,
        y=polinomio(xline),
        line=dict(color='green', dash='dash')
    )
    return (coeff[0], coeff[1], R2, figline)

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

selected_filenames = st.multiselect('Select files to calculate ACR', filenames)


@st.cache_data
def read_dataframes(files):
    dfs = []
    capacitors = []
    integration_times = []
    for file in files:
        file = os.path.join("Measurements", "Shots", file)
        # confirm the rows to skip
        file0 = open(file)
        firstlines = file0.readlines()
        file0.close()
        for line in firstlines:
            if line.startswith("Rank used:"):
                rank = line[11:-1]
                break
        if rank == '1':
            capacitors.append(10 / 1000)
        elif rank == '2':
            capacitors.append(30 / 1000)
        elif rank == '4':
            capacitors.append(60 / 1000)
        elif rank == '8':
            capacitors.append(1.8)
        for line in firstlines:
            if line.startswith("Integration time:"):
                integration_time = line[18:-3]
                integration_times.append(int(integration_time))
        for n, line in enumerate(firstlines):
            if line.startswith('idx,dt_us'):
                lines_to_skip = n
                break
        df = pd.read_csv(file, skiprows=lines_to_skip)
        dfs.append(df)
    return dfs, capacitors, integration_times


dfs, capacitors, integration_times = read_dataframes(selected_filenames)

cutoff = st.selectbox('cut off', [0.5, 8, 10, 20, 40, 100, 150], index=4)

OF = st.number_input('Known OF (1 means it will be used the gantry rotation method)', format='%.3f')

dfis = []
for i in range(len(dfs)):
    df_orig = dfs[i]
    capacitor = capacitors[i]
    integration_time = integration_times[i]
    df_orig["dt_s"] = df_orig.df_us / 1000000
    df = df_orig.loc[:, ['idx', 'dt_s', 'ch0_V', 'ch1_V']]
    df.columns = ['Number', 'Time', 'ch0', 'ch1']
    last_time = df.iloc[-1, 1]
    zeros = df.loc[(df.Time < 1) | (df.Time > last_time - 1), 'ch0':].mean()
    dfchz = df.loc[:, 'ch0':] - zeros
    dfchz.columns = ['ch0z', 'ch1z']
    dfz = pd.concat([df, dfchz], axis=1)

    dfz['sensorcharge'] = dfz.ch0z * capacitor
    dfz['cerenkovcharge'] = dfz.ch1z * capacitor

    dfz['chunk'] = dfz.Number // (300000 / integration_time)
    group = dfz.groupby('chunk')
    dfg = group.agg({'Time': np.median,
                     'ch0z': np.sum,
                     'ch1z': np.sum})
    dfg['time_min'] = group['Time'].min()
    dfg['time_max'] = group['Time'].max()
    dfg['ch0diff'] = dfg.ch0z.diff()
    starttimes = dfg.loc[dfg.ch0diff > cutoff, 'time_min']
    finishtimes = dfg.loc[dfg.ch0diff < -cutoff, 'time_max']
    stss = [starttimes.iloc[0]] + list(starttimes[starttimes.diff() > 2])
    sts = [t - 0.08 for t in stss]
    ftss = [finishtimes.iloc[0]] + list(finishtimes[finishtimes.diff() > 2])
    fts = [t + 0.04 for t in ftss]

    # Find pulses
    maxvaluech = dfz.loc[(dfz.Time < sts[0] - 1) | (dfz.Time > fts[-1] + 1), 'ch0z'].max()
    dfz['pulse'] = dfz.ch0z > maxvaluech * 1.05
    dfz.loc[dfz.pulse, 'pulsenum'] = 1
    dfz.fillna({'pulsenum': 0}, inplace=True)
    dfz['pulsecoincide'] = dfz.loc[dfz.pulse, 'Number'].diff() == 1
    dfz.fillna({'pulsecoincide': False}, inplace=True)
    dfz['singlepulse'] = dfz.pulse & ~dfz.pulsecoincide

    for (n, (s, f)) in enumerate(zip(sts, fts)):
        dfz.loc[(dfz.Time > s) & (dfz.Time < f), 'shot'] = n

    dfi = dfz.groupby('shot').agg({'sensorcharge': np.sum,
                                   'cerenkovcharge': np.sum,
                                   'singlepulse': np.sum})
    dfis.append(dfi)

dfit = pd.concat(dfis)
dfit.reset_index(inplace=True, drop=True)
st.dataframe(dfit)

if OF == 1:
    # Here I have to put all the code to calc ACR based in rotations
    xnow = dfit.cerenkovcharge
    ynow = dfit.sensorcharge
    fig0 = go.Figure()
    go1 = go.Scatter(
        x=xnow,
        y=ynow,
        mode='markers'
    )
    fig0.add_traces(go1)
    ACR, ind, R2now, go2 = R2(xnow, ynow)
    fig0.add_traces(go2)
    fig0.add_annotation(
        x=(xnow.max() + xnow.min()) / 2 + 10,
        y=(ynow.max() + ynow.min()) / 2,
        text=r'y = %.3f x + %.3f' % (ACR, ind),
        showarrow=False,
        font=dict(
            size=18,
            color='red'
        )
    )
    fig0.add_annotation(
        x=(xnow.max() + xnow.min()) / 2 + 10,
        y=(ynow.max() + ynow.min()) / 2 - 50,
        text='R2 = %.3f' % (R2now),
        showarrow=False,
        font=dict(
            size=18,
            color='red'
        )
    )
    fig0.update_xaxes(title='ch1/Cerenkov')
    fig0.update_yaxes(title='ch0/Sensor')
    st.plotly_chart(fig0)


else:
    index10 = st.multiselect('Select index large field (ex. 10x10)', dfit.index)
    index3 = st.multiselect('Select index small field (ex. 3x3)', dfit.index)

    s10 = dfit.iloc[index10, 0].mean()
    s3 = dfit.iloc[index3, 0].mean()
    c10 = dfit.iloc[index10, 1].mean()
    c3 = dfit.iloc[index3, 1].mean()

    ACR = (s10 * OF - s3) / (c10 * OF - c3)

st.write("ACR is: %.3f" % ACR)