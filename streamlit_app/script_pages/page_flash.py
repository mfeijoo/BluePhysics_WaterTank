import time
import streamlit as st
import os
import time
import plotly.express as px
from datetime import datetime
import numpy as np
from glob import glob
import pandas as pd
import re
from helpers import calc_shots_integrals
from protocol import counts_to_volts


st.logo(image="images/logo.png", icon_image="images/icon.png")

st.title('Measure Flash')

mgr = st.session_state.mgr
connected = mgr.is_connected()

measurements_folder = os.path.join("Measurements", "Shots")
of_table_folder = os.path.join("Measurements", "OF_tables")

if 'measuring_flash' not in st.session_state:
    st.session_state['measuring_flash'] = False

if 'is_started' not in st.session_state:
    st.session_state['is_started'] = False

if 'integration_time' not in st.session_state:
    st.session_state['integration_time'] = None

st.header("Flash Measurement")

filename_prefix = st.text_input("Filename prefix:", value="Flash_")
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
st.write(f"Complete filename preview: {filename_prefix}_{current_time}.csv")

def sanitize_description():
    text = st.session_state.flash_description_addition
    cleaned = text.replace("{", "").replace("}", "")
    st.session_state.flash_description_addition = cleaned

description_addition = st.text_area("Add description to file header:", on_change=sanitize_description, key="flash_description_addition", placeholder="Characters not permitted: { }")
description_addition = "{" + description_addition + "}"

concurrent_plot = st.empty()

pulse_threshold_v = st.number_input(
    "Pulse threshold (V):",
    value=-9.0,
    step=0.1,
    format="%.3f",
)
acr_value = float(st.session_state.get("acr_value", 1.0))
calibration_factor = float(st.session_state.get("calibration_factor", 1.0))
target_pulses = st.number_input(
    "Target pulses:",
    min_value=1,
    value=1,
    step=1,
    format="%d",
)
target_dose_cgy = st.number_input(
    "Target dose (cGy):",
    min_value=0.1,
    value=0.1,
    step=0.1,
    format="%.3f",
)

st.caption(
    f"Pulse-count settings sent to firmware via RSPT: threshold={pulse_threshold_v:.3f} V, "
    f"ACR={acr_value:.3f}, calibration factor={calibration_factor:.3f}, "
    f"target pulses={int(target_pulses)}, target dose={target_dose_cgy:.3f} cGy"
)

signal_cols = st.columns(2)
with signal_cols[0]:
    if st.button("Set Flash Signal HIGH", disabled=not connected):
        mgr.send_cmd("pin21L;")
        st.success("Flash signal set to HIGH.")
with signal_cols[1]:
    if st.button("Set Flash Signal LOW", disabled=not connected):
        mgr.send_cmd("pin21H;")
        st.success("Flash signal set to LOW.")

cols = st.columns([3, 3, 3, 1], vertical_alignment="center")
with cols[1]:
    if st.button('Start', disabled=(not connected) or mgr.rs_capture_active):
        st.session_state['measuring_flash'] = True
        rsp_cmd = f"rspt{pulse_threshold_v:.3f},{acr_value:.3f},{calibration_factor:.3f},{int(target_pulses)},{target_dose_cgy:.3f};"
        start_result = mgr.start_rs_capture(command=rsp_cmd)
        if not start_result.get("ok"):
            st.error(start_result.get("error", "Unable to start measurement."))
with cols[2]:
    if st.button('Stop', disabled=(not connected) or (not mgr.rs_capture_active)):
        st.session_state['measuring_flash'] = False
        stop_result = mgr.stop_rs_capture()
        st.session_state.rs_session_result = stop_result
        if stop_result.get("ok"):
            st.success("Measurement stopped.")
        else:
            st.error(stop_result.get("error", "Unable to stop measurement."))
        concurrent_plot = st.empty()
        samples = stop_result.get("samples", [])
        rows = [
            {
                "idx": s.idx,
                "dt_us": s.dt_us,
                "ch0_counts": s.ch0,
                "ch1_counts": s.ch1,
                "ch0_V": counts_to_volts(s.ch0),
                "ch1_V": counts_to_volts(s.ch1),
            }
            for s in samples
        ]
        if rows:
            df_rawdata = pd.DataFrame(rows)
            df_rawdata = df_rawdata.iloc[10:, :].copy()
            df_rawdata["dt_s"] = df_rawdata.dt_us / 1000000
            df = df_rawdata.loc[:, ['idx', 'dt_s', 'ch0_V', 'ch1_V']]
            df.columns = ['Number', 'Time', 'ch0', 'ch1']
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            integration_value = df_rawdata["dt_us"].diff()
            st.session_state.integration_time = integration_value

            header = f"""Flash
Date and time: {current_time}
Description: {description_addition}
ACR used: {st.session_state.get("acr_value", 1.0)}
Calibration factor used: {st.session_state.get("calibration_factor", 1.0)}
Pulse threshold used: {pulse_threshold_v:.3f}
Target pulses used: {int(target_pulses)}
Target dose used (cGy): {target_dose_cgy:.3f}
Rank used: {st.session_state.get("rank_value", 1)}
Integration time: {integration_value} us
"""
            # file_name = f"Output_Factor_{energy_used}_{field_size_cm}x{field_size_cm}_{current_time}.csv"
            file_name = f"{filename_prefix}{current_time}.csv"
            os.makedirs(measurements_folder, exist_ok=True)
            file_path = os.path.join(measurements_folder, file_name)
            with open(file_path, 'w') as f:
                # Write header lines
                f.writelines(header)
                # Append DataFrame
                df.to_csv(f, index=False)
            st.toast("File downloaded successfully!")
            st.session_state['flash_file_to_analyze'] = file_path
            time.sleep(0.5)
            st.rerun()



while st.session_state['measuring_flash']:
    time.sleep(0.5)
    buffer_result = mgr.get_rs_capture_buf()
    if not buffer_result.get("ok"):
        continue
    samples = buffer_result.get("samples", [])
    rows = [
        {
            "idx": s.idx,
            "dt_us": s.dt_us,
            "ch0_counts": s.ch0,
            "ch1_counts": s.ch1,
            "ch0_V": counts_to_volts(s.ch0),
            "ch1_V": counts_to_volts(s.ch1),
        }
        for s in samples
    ]
    if rows:
        df_rawdata_concurrent = pd.DataFrame(rows)
        if len(df_rawdata_concurrent) < 10:
            continue
        df_rawdata_concurrent_cropped = df_rawdata_concurrent.iloc[10:, :].copy()
        df_rawdata_concurrent_cropped["dt_s"] = df_rawdata_concurrent_cropped.dt_us / 1000000
        df = df_rawdata_concurrent_cropped.loc[:, ['idx', 'dt_s', 'ch0_V', 'ch1_V']]
        df.columns = ['Number', 'Time', 'ch0', 'ch1']
        max_time = df['Time'].max()
        df = df[df['Time'] >= (max_time - 30)].copy()
        df['time_bin'] = (df['Time'] / 0.5).astype(int)
        df = df.groupby('time_bin').agg({'Time': 'median', 'ch0': 'sum', 'ch1': 'sum'}).reset_index(drop=True)
        plot_concurrent = px.scatter(df, x='Time', y='ch0',
                                     labels={'Time': 'Time (s)', 'Dose': 'Charge proportional to dose (nC)'})
        concurrent_plot.plotly_chart(plot_concurrent, key=f"flash_live_{time.time()}")

def extract_datetime_from_name(path):
    base = os.path.basename(path)
    name, _ = os.path.splitext(base)
    try:
        # Try to find date in format YYYY-MM-DD_HH-MM-SS at the end of the filename
        return datetime.strptime(base[-19:], "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        # fallback: find it anywhere in the name just in case
        m = re.search(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", base)
        return datetime.strptime(m.group(0), "%Y-%m-%d_%H-%M-%S") if m else datetime.min

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
    return df, capacitor, float(integration_time), acr_used

list_original_files = glob(os.path.join(measurements_folder, "*.csv"))
# Sort files by date, newest first
list_original_files = sorted(list_original_files, key=extract_datetime_from_name, reverse=True)

# Show only filenames in the dropdown
list_names = ['select a file...'] + [os.path.basename(f) for f in list_original_files]

file_now_name = st.selectbox('...Or select file to create Flash df', list_names)

if file_now_name != 'select a file...':
    file_now = os.path.join("Measurements", "Shots", file_now_name)
    st.session_state['flash_file_to_analyze'] = file_now
    dforig, capacitator, integration_time_us, acr_used = read_dataframe(file_now)
else:
    file_now = 'select a file...'
    acr_used = st.session_state.get("acr_value", 1.0)
    capacitator = st.session_state.get("rank_value", 1.0)
    integration_time_us = st.session_state.get("integration_time", 1.0)

if 'flash_file_to_analyze' in st.session_state:

    cutoff_now = st.selectbox('Select cut off: ', [0.5,8, 10, 20, 40, 100, 150], index=4)
    ACR_now = st.number_input('Select ACR value:',
                              min_value=0.00,
                              max_value=3.00,
                              value=acr_used,
                              format="%.3f"
                              )

    plotg, dfi, fig2 = calc_shots_integrals(
        st.session_state['flash_file_to_analyze'],
        ACR=ACR_now,
        cutoff=cutoff_now,
        calibration_factor=st.session_state.get("calibration_factor", 1.0),
    )
    st.plotly_chart(plotg, key="flash_result_main")
    pulseson = st.checkbox('See pulses')

    if pulseson:
        st.plotly_chart(fig2, key="flash_result_pulses")
