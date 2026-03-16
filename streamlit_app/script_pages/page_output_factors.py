import time
import streamlit as st
import os
import time
import plotly.express as px
# import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from glob import glob
import pandas as pd
import re
from helpers import calc_shots_integrals
from access_logging import log_user_action

def show():

    st.logo(image="images/logo.png", icon_image="images/icon.png")

    st.title('Output Factors')

    # Check validity of license and whether we should check again
    if "license_next_check" in st.session_state and (st.session_state["license_next_check"] < datetime.utcnow()):
        # Verify license validity
        try:
            valid, next_check = st.session_state['license'].activate_license()
        except Exception as err:
            st.error(f"Error checking validity of license. {err}")
            st.stop()
        st.session_state['licenses_valid'] = valid
        st.session_state['license_next_check'] = next_check
    if not st.session_state['licenses_valid']:
        st.error("Loaded license is not valid or has expired")
        st.stop()


    if 'field_size' not in st.session_state:
        st.info('Field size used isn\'t saved. First save it on page \'Center\'.')
        st.stop()

    center = st.session_state['center']
    watertank = st.session_state['watertank']
    speed_go_to_start = (30.0, 30.0, 30.0)
    device = st.session_state['device']
    data_folder = os.path.join("Measurements", "Shots")
    if 'is_started' not in st.session_state:
        st.session_state['is_started'] = False

    now = time.time()
    if device.zero_done is None:
        st.warning("Device hasn't been zeroed yet")
        if st.button(f"Zero {device.name}"):
            device.set_zero()
            st.rerun()
    elif now - device.zero_done > 30 * 60:
        st.warning(f"Last zero of the device has been done {(now - device.zero_done) // 60} minutes ago")
        if st.button(f"Zero {device.name}"):
            device.set_zero()
            st.rerun()


    # st.write(f"#### Field size used: {field_size / 10} cm")
    current_pos = watertank.get_position()
    collimator_system = st.session_state['collimation_type_used']
    energy_used = st.session_state['energy_type_used']

    # energy_used = st.text_input("Energy used: ", placeholder = "No energy introduced")
    depth = center.top[2]
    center_top_pos = center.get_center(depth)

    st.write(f"#### Collimation System: {collimator_system}")
    st.write(f"#### Energy used: {energy_used}")
    st.markdown(f"""
    Shots will be measured at:\n
    Axis X: **{center_top_pos[0]:.2f}** mm\n
    Axis Y: **{center_top_pos[1]:.2f}** mm\n
    Axis Z: **{center_top_pos[2]:.2f}** mm
    """)

    filename_addition = st.text_input("Add to filename:")
    if filename_addition != "":
        filename_prefix = f"Output_Factor_{energy_used}_{filename_addition}_"
        st.write(f"File name prefix: {filename_prefix}...")
    else:
        filename_prefix = f"Output_Factor_{energy_used}_"
        st.write(f"File name prefix: {filename_prefix}...")

    def sanitize_description():
        text = st.session_state.description_addition
        cleaned = text.replace("{", "").replace("}", "")
        st.session_state.description_addition = cleaned

    description_addition = st.text_area("Add description to file header:", on_change=sanitize_description, key="description_addition", placeholder="Characters not permitted: { }")
    description_addition = "{" + description_addition + "}"

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

    list_original_files = glob('Measurements/Shots/*.csv')
    # Filter out files starting with "dfOF"
    list_original_files = [f for f in list_original_files if not os.path.basename(f).startswith("dfOF")]
    # Sort files by date, newest first
    list_original_files = sorted(list_original_files, key=extract_datetime_from_name, reverse=True)

    # Show only filenames in the dropdown
    list_names = ['select a file...'] + [os.path.basename(f) for f in list_original_files]

    file_now_name = st.selectbox('...Or select file to create OF df', list_names)

    if file_now_name != 'select a file...':
        # Reconstruct the full path
        file_now = os.path.join("Measurements", "Shots", file_now_name)
        st.session_state['file_to_analyze'] = file_now
        lines = []
        with open(file_now) as f:
            for i in range(40):
                line = f.readline()
                if not line:
                    break
                lines.append(line)
        header_lines_to_save = []
        for line in lines:
            if line.strip() == "" or line[0].isdigit() or line.startswith("Time,"): # Assuming data starts with Time column or is numbers
                 break
            header_lines_to_save.append(line)
        
        for n, li in enumerate(lines):
            if li.startswith("Field Size X Top: "):
                x_size_from_file = float(li[18:-4])
                continue
            if li.startswith("Field Size Y Top: "):
                y_size_from_file = float(li[18:-4])
                break
    else:
        file_now = 'select a file...'

    if device.type == "DUMMY":
        with st.expander("Dummy Device Simulation Controls"):
            device.shot_simulation_mode = st.checkbox("Simulate Shots", value=device.shot_simulation_mode)
            device.shot_on_time = st.number_input("Shot ON Time (s)", value=device.shot_on_time, min_value=0.1, step=0.1)
            device.shot_off_time = st.number_input("Shot OFF Time (s)", value=device.shot_off_time, min_value=0.1, step=0.1)

    concurrent_plot = st.empty()

    cols = st.columns([3, 3, 3, 1], vertical_alignment="center")
    with cols[1]:
        if st.button('Start'):
            start_point = center.get_center(depth)
            if start_point != current_pos:
                watertank.set_speed(speed_go_to_start)
                watertank.set_position(start_point)
                time.sleep(2)
            device.clear_global_buffer()
            # Ensure static position simulation for dummy device
            if hasattr(device, 'clear_movement_parameters'):
                device.clear_movement_parameters()
            if hasattr(device, 'set_simulation_position'):
                device.set_simulation_position(start_point)
                
            st.session_state['is_started'] = True
            device.start_reading_thread()
            # st.rerun()
    with cols[2]:
        if st.button('Stop'):
            st.session_state['is_started'] = False
            device.stop_reading_data()
            concurrent_plot = st.empty()
            df_rawdata = device.get_formatted_data()
            start_point = center.get_center(depth)
            header = f"""Output Factor
Site: {st.session_state["accelerator_site"]}
Accelerator manufacturer: {st.session_state["accelerator_manufacturer"]}
Accelerator model: {st.session_state["accelerator_model"]}
Collimation system: {st.session_state["collimation_type_used"]}
Energy system: {energy_used}
SSD: {st.session_state["ssd_used_saved"]} mm
SAD: {st.session_state["sad_used_saved"]} mm
Description: {description_addition}
Watertank type: {watertank.type}
Measured at X: {start_point[0]}
Measured at Y: {start_point[1]}
Measured at Z: {start_point[2]}
Energy used: {energy_used}
ACR used: {device.acr_value}
Rank used: {device.rank_used}
Mask for ch0z from last set_zero: {device.zero_value_ch0} 
Mask for ch1z from last set_zero: {device.zero_value_ch1} 
Maximum non pulse: {device.maximum_non_pulse}
Maximum ch0 noise: {device.maximum_ch0}
Std for Dose from last set_zero: {device.Dose_zero_std}
Center top X: {center.top[0]:.2f} mm
Center top Y: {center.top[1]:.2f} mm
Center top Z: {center.top[2]:.2f} mm
Field Size X Top: {st.session_state['field_size_top_X']:.2f} mm
Field Size Y Top: {st.session_state['field_size_top_Y']:.2f} mm
Field Sclin Top: {st.session_state['field_sclin_top']:.2f} mm
Center bottom X: {center.bottom[0]:.2f} mm
Center bottom Y: {center.bottom[1]:.2f} mm
Center bottom Z: {center.bottom[2]:.2f} mm
Field Size X Bottom: {st.session_state['field_size_bottom_X']:.2f} mm
Field Size Y Bottom: {st.session_state['field_size_bottom_Y']:.2f} mm
Field Sclin Bottom: {st.session_state['field_sclin_bottom']:.2f} mm
"""
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            # file_name = f"Output_Factor_{energy_used}_{field_size_cm}x{field_size_cm}_{current_time}.csv"
            file_name = f"{filename_prefix}{current_time}.csv"
            os.makedirs(data_folder, exist_ok=True)
            file_path = os.path.join(data_folder, file_name)
            with open(file_path, 'w') as f:
                # Write header lines
                f.writelines(header)
                # Append DataFrame
                df_rawdata.to_csv(f, index=False)
            st.toast("File downloaded successfully!")
            log_user_action(f"Measured shots, info: {energy_used}.", True)
            st.session_state['file_to_analyze'] = file_path



    while st.session_state['is_started']:
        time.sleep(0.3)
        df_rawdata_concurrent = device.get_formatted_data(device.group_data_value)
        plot_concurrent = px.scatter(df_rawdata_concurrent.iloc[:-1, :], x='Time', y='Dose',
                                     labels={'Time': 'Time (s)', 'Dose': 'Charge proportional to dose (nC)'})
        concurrent_plot.plotly_chart(plot_concurrent, key=f"of_live_{time.time()}")

    if 'file_to_analyze' in st.session_state:

        cutoff_now = st.selectbox('Select cut off: ', [0.5,8, 10, 20, 40, 100, 150], index=4)
        ACR_now = st.number_input('Select ACR value:',
                                  min_value=0.00,
                                  max_value=3.00,
                                  value=device.acr_value,
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

        if file_now != 'select a file...':
            x_size = x_size_from_file
            y_size = y_size_from_file
        else:
            x_size = st.session_state['field_size_top_X']
            y_size = st.session_state['field_size_top_Y']

        if field_shape == 'rectangular':
            Sclin = (x_size * y_size)**0.5
        else:
            Sclin = (np.pi)**0.5 * (x_size + y_size)/4


        columns_now = list(dfi.columns)
        dfi['center_x_mm'] = center.top[0]
        dfi['center_y_mm'] = center.top[1]
        dfi['field_size_x_mm'] = st.session_state['field_size_top_X']
        dfi['field_size_y_mm'] = st.session_state['field_size_top_Y']
        
        # Add nominal field size columns
        nominal_x = st.session_state.get('field_size', [0, 0])[0]
        nominal_y = st.session_state.get('field_size', [0, 0])[1]
        dfi['nominal_field_size_x_cm'] = nominal_x
        dfi['nominal_field_size_y_cm'] = nominal_y

        columns_disabled = columns_now + ['center_x_mm', 'center_y_mm',]
        dfi['Sclin_mm'] = Sclin

        st.write('Change the field size (Sclin) in mm')
        dfi_edited = st.data_editor(dfi.round(2), hide_index = True,  disabled=columns_disabled)

        text_file_name = st.text_input('add free text for file')

        st.write(f"File name prefix for OF table: dfOF_{text_file_name}_{energy_used}_{depth}_...")
        if st.button('Save OF Data'):
            current_time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f'dfOF_{text_file_name}_{energy_used}_{depth}_{current_time_now}.csv'
            file_path = os.path.join(data_folder, file_name)
            
            # Save with header if available
            with open(file_path, 'w') as f:
                if file_now != 'select a file...':
                     f.writelines(header_lines_to_save)
                dfi_edited.to_csv(f, index=False)
            
            st.toast(f"File saved: {file_name}")


