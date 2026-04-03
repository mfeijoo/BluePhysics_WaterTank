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

st.title('Measure Output Factors')

mgr = st.session_state.mgr
connected = mgr.is_connected()

measurements_folder = os.path.join("Measurements", "Shots")
of_table_folder = os.path.join("Measurements", "OF_tables")

if 'measuring_OF' not in st.session_state:
    st.session_state['measuring_OF'] = False

if 'is_started' not in st.session_state:
    st.session_state['is_started'] = False

st.header("OF Measurement")

filename_prefix = st.text_input("Filename prefix:", value="Output_Factor_")
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
st.write(f"Complete filename preview: {filename_prefix}_{current_time}.csv")

def sanitize_description():
    text = st.session_state.description_addition
    cleaned = text.replace("{", "").replace("}", "")
    st.session_state.description_addition = cleaned

description_addition = st.text_area("Add description to file header:", on_change=sanitize_description, key="description_addition", placeholder="Characters not permitted: { }")
description_addition = "{" + description_addition + "}"

concurrent_plot = st.empty()

cols = st.columns([3, 3, 3, 1], vertical_alignment="center")
with cols[1]:
    if st.button('Start', disabled=(not connected) or mgr.rs_capture_active):
        st.session_state['measuring_OF'] = True
        start_result = mgr.start_rs_capture()
        if not start_result.get("ok"):
            st.error(start_result.get("error", "Unable to start measurement."))
with cols[2]:
    if st.button('Stop', disabled=(not connected) or (not mgr.rs_capture_active)):
        st.session_state['measuring_OF'] = False
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
            df_rawdata["dt_s"] = df_rawdata.dt_us / 1000000
            df = df_rawdata.loc[:, ['idx', 'dt_s', 'ch0_V', 'ch1_V']]
            df.columns = ['Number', 'Time', 'ch0', 'ch1']
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            integration_value = rows[0]["dt_us"]

            header = f"""Output Factor
Date and time: {current_time}
Description: {description_addition}
ACR used: {st.session_state.get("acr_value", 1.0)}
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
            st.session_state['file_to_analyze'] = file_path



while st.session_state['measuring_OF']:
    time.sleep(0.3)
    buffer_result = mgr.get_rs_capture_buff()
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
        df = df_rawdata.loc[:, ['idx', 'dt_s', 'ch0_V', 'ch1_V']]
        df.columns = ['Number', 'Time', 'ch0', 'ch1']
        df['chunk'] = df.Number // 400
        df = df.groupby('chunk').agg({'Time': 'median', 'ch0': 'sum', 'ch1': 'sum'})
        plot_concurrent = px.scatter(df.iloc[:-1, :], x='Time', y='ch1',
                                     labels={'Time': 'Time (s)', 'Dose': 'Charge proportional to dose (nC)'})
        concurrent_plot.plotly_chart(plot_concurrent, key=f"of_live_{time.time()}")

st.header("Create OF table")

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
    return df, capacitor, int(integration_time), acr_used

list_original_files = glob(os.path.join(measurements_folder, "*.csv"))
# Sort files by date, newest first
list_original_files = sorted(list_original_files, key=extract_datetime_from_name, reverse=True)

# Show only filenames in the dropdown
list_names = ['select a file...'] + [os.path.basename(f) for f in list_original_files]

file_now_name = st.selectbox('...Or select file to create OF df', list_names)

if file_now_name != 'select a file...':
    file_now = os.path.join("Measurements", "Shots", file_now_name)
    st.session_state['file_to_analyze'] = file_now
    dforig, capacitator, integration_time_us, acr_used = read_dataframe(file_now)
else:
    file_now = 'select a file...'
    acr_used = st.session_state.get("acr_value", 1.0)

if 'file_to_analyze' in st.session_state:

    cutoff_now = st.selectbox('Select cut off: ', [0.5,8, 10, 20, 40, 100, 150], index=4)
    ACR_now = st.number_input('Select ACR value:',
                              min_value=0.00,
                              max_value=3.00,
                              value=acr_used,
                              format="%.3f"
                              )

    plotg, dfi, fig2 =  calc_shots_integrals(st.session_state['file_to_analyze'],
                                             ACR = ACR_now,
                                             cutoff=cutoff_now
                                             )
    st.plotly_chart(plotg, key="of_result_main")
    pulseson = st.checkbox('See pulses')

    if pulseson:
        st.plotly_chart(fig2, key="of_result_pulses")

    # A way to upload the file sizes of each shot
    #first select is these are square files or circle files
    field_shape = st.radio('Field Shape', ['rectangular', 'circular'])
    # calculate Sclin

    columns_now = list(dfi.columns)
    dfi['center_x_mm'] = 0.0
    dfi['center_y_mm'] = 0.0
    dfi['field_size_x_mm'] = 10.0
    dfi['field_size_y_mm'] = 10.0

    # Add nominal field size columns
    nominal_x = 1.0
    nominal_y = 1.0
    dfi['nominal_field_size_x_cm'] = nominal_x
    dfi['nominal_field_size_y_cm'] = nominal_y

    columns_disabled = columns_now


    st.write('Change the field size (Sclin) in mm')
    dfi_edited = st.data_editor(dfi.round(2), hide_index = True,  disabled=columns_disabled)
    if field_shape == 'rectangular':
        Sclin = (dfi_edited['field_size_x_mm'] * dfi_edited['field_size_y_mm']) ** 0.5
    else:
        Sclin = (np.pi) ** 0.5 * (dfi_edited['field_size_x_mm']  + dfi_edited['field_size_y_mm']) / 4
    dfi_edited['Sclin_mm'] = Sclin

    text_file_name = st.text_input('add free text for file')

    st.write(f"File name prefix for OF table: dfOF_{text_file_name}_...")
    if st.button('Save OF Data'):
        current_time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f'dfOF_{text_file_name}_{current_time_now}.csv'
        file_path = os.path.join(of_table_folder, file_name)

        # Save with header if available
        with open(file_path, 'w') as f:
            if 'file_to_analyze' in st.session_state:

                header_lines_to_save = f"""Output Factor Table
Date and time: {current_time_now}
ACR used: {ACR_now}
Capacitator used: {capacitator}
Integration time: {integration_time_us} us
Cutoff: {cutoff_now}
"""
                f.writelines(header_lines_to_save)
            dfi_edited.to_csv(f, index=False)

        st.toast(f"File saved: {file_name}")


