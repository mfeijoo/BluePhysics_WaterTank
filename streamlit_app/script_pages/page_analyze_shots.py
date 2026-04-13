import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from glob import glob
import os
import re
from datetime import datetime



st.logo(image="images/logo.png", icon_image="images/icon.png")

st.title('Blue Physics Analysis')

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

filenames = [s for s in filenames if not s.startswith("dfOF")]

filenow = st.selectbox('Select File to Analyze', filenames)

#Take a quick look at the raw data
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

dforig, capacitor, inegration_time_us = read_dataframe(os.path.join("Measurements", "Shots", filenow))
# dforig["dt_s"] = dforig.df_us / 1000000
# df = dforig.loc[:, ['idx', 'dt_s', 'ch0_V', 'ch1_V']]
# df.columns = ['Number', 'Time', 'ch0', 'ch1']
df = dforig.copy()
st.dataframe(df)

intTime = df.Time.diff().mean() * 1000000
st.write('Average integration Time: %.2f microseconds' %intTime)

last_Time = df.iloc[-1,1]
zeros = df.loc[(df.Time < 1) | (df.Time > last_Time -1), 'ch0':].mean()
dfzeros = df.loc[:, 'ch0':] - zeros
dfzeros.columns = ['ch0z', 'ch1z']
dfz = pd.concat([df, dfzeros], axis = 1)

showpulses = st.checkbox('Show Pulses', value = False)
if showpulses:
    dfz0 = dfz.loc[:, ['Time', 'ch0z']]
    dfz0.columns = ['Time', 'signal']
    dfz0['ch'] = 'ch0z'
    dfz1 = dfz.loc[:, ['Time', 'ch1z']]
    dfz1.columns = ['Time', 'signal']
    dfz1['ch'] = 'ch1z'
    dfztp = pd.concat([dfz0, dfz1])
    fig1 = px.line(dfztp, x='Time', y='signal', color = 'ch', markers = True)
    fig1.update_traces(marker=dict(size=4))
    fig1.update_xaxes(title = 'Time (s)')
    fig1.update_yaxes(title = 'Voltage (V)')
    st.plotly_chart(fig1)

group = st.checkbox('group every 300 ms', value = True)
if group:
    dfz['chunk'] = dfz.Number // int(300000/inegration_time_us)
    #dfz['chunk'] = dfz.Number // 5
    dfg = dfz.groupby('chunk').agg({'Time':np.median, 'ch0z':np.sum, 'ch1z':np.sum})
    dfg0 = dfg.loc[:,['Time', 'ch0z']]
    dfg0.columns = ['Time', 'signal']
    dfg0['ch'] = 'sensor'
    dfg1 = dfg.loc[:,['Time', 'ch1z']]
    dfg1.columns = ['Time', 'signal']
    dfg1['ch'] = 'cerenkov'
    dfgtp = pd.concat([dfg0, dfg1])
    fig2 = px.line(dfgtp, x='Time', y='signal', color = 'ch', markers = True)
    fig2.update_xaxes(title = 'Time (s)')
    st.plotly_chart(fig2)
