import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from glob import glob
import os
import re
import yaml
from datetime import datetime


st.title('Calculate OF')

st.logo(image="images/logo.png", icon_image="images/icon.png")

files = glob(os.path.join("Measurements", "OF_tables", "*.csv"))

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


# --- Helper Functions ---
def read_csv_safe(file_path):
    """Reads CSV, skipping header lines if present."""
    try:
        with open(file_path, 'r') as f:
            # Read first few lines to detect header
            header_count = 0
            pos = f.tell()
            for i in range(50): # Check first 50 lines max
                line = f.readline()
                # simplistic check: if line doesn't start with a number and contains "Time" or common CSV headers, it might be the start
                # But our header is text. Real data starts with headers "sensorcharge_nC,..."
                if "sensorcharge_nC" in line: # Found the CSV header
                    break
                header_count += 1
            f.seek(pos) # Reset to start to read properly or skip

        # if we found the header line at header_count, we skip distinct lines before it?
        # actually pandas read_csv 'header' arg is row number(0-indexed) containing the header
        return pd.read_csv(file_path, header=header_count)
    except Exception as e:
        st.error(f"Error reading {os.path.basename(file_path)}: {e}")
        return pd.DataFrame()

@st.cache_data
def process_dataset(files, grouping_col, new_acr=None):
    """Reads and processes a set of files. Returns (df_grouped, df_raw)."""
    dfs = []
    for file in files:
        df = read_csv_safe(file)
        if not df.empty:
            # Add filename for reference
            df['filename'] = os.path.basename(file)
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(), pd.DataFrame()

    df_total = pd.concat(dfs)

    # Ensure nominal columns exist if missing (backwards compatibility)
    if 'nominal_field_size_x_cm' not in df_total.columns:
        df_total['nominal_field_size_x_cm'] = np.nan
    if 'nominal_field_size_y_cm' not in df_total.columns:
        df_total['nominal_field_size_y_cm'] = np.nan

    if new_acr is not None:
        df_total["charge_prop_dose_nC"] = df_total.sensorcharge_nC - df_total.cerenkovcharge_nC * new_acr

    # Grouping
    if grouping_col not in df_total.columns:
        st.warning(f"Grouping column '{grouping_col}' not found in data. Using Sclin_mm.")
        grouping_col = 'Sclin_mm'

    df_grouped = df_total.groupby(grouping_col).mean(numeric_only=True).reset_index()
    # Calculate error (SEM)
    if grouping_col in df_total.columns:
         df_grouped["error"] = df_total.groupby(grouping_col)["charge_prop_dose_nC"].sem().reset_index()["charge_prop_dose_nC"]
    else:
         df_grouped["error"] = 0

    return df_grouped, df_total

def get_reference_label(row):
    """Helper to format reference field options."""
    if pd.notnull(row.get('nominal_field_size_x_cm')) and pd.notnull(row.get('nominal_field_size_y_cm')) and row['nominal_field_size_x_cm'] != 0:
        return f"{row['nominal_field_size_x_cm']} x {row['nominal_field_size_y_cm']}"
    return f"{row['Sclin_mm']:.2f} mm (Sclin)"

# --- Session State for Datasets ---
if 'measurement_sets' not in st.session_state:
    st.session_state['measurement_sets'] = []

def add_measurement_set():
    new_id = len(st.session_state['measurement_sets']) + 1
    st.session_state['measurement_sets'].append({
        'id': new_id,
        'name': f"Set {new_id}",
        'files': [],
        'color': '#1f77b4', # Default blue-ish
        'ref_value': None
    })

def remove_measurement_set(index):
    st.session_state['measurement_sets'].pop(index)

def get_sensor_defaults(slot: int):
    yaml_path = os.path.join("Measurements", "Shots_Other_Detectors", "Other_Detectors_OF.yaml")
    key = {2: "sensor2", 3: "sensor3"}.get(slot)
    if key is None:
        print("Key is none")
        return None
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        entry = data[key]
        nf = entry["nominal_fields"]
        ofs = entry["ofs"]

        if not isinstance(nf, list) or not isinstance(ofs, list) or len(nf) != len(ofs):
            print("Types of yaml are not lists")
            return None

        print("Trasnsforming into string")

        def to_csv(seq):
            nums = [float(x) for x in seq]  # validate/coerce
            # normalize numbers; no spaces
            return ",".join(
                f"{v:.15g}".rstrip("0").rstrip(".") if "." in f"{v:.15g}" else f"{v:.15g}" for v in nums)

        print(to_csv(nf))
        return to_csv(ofs), to_csv(nf)
    except Exception as e:
        print("Exception:", e)
        return None

# --- UI Layout ---

# Global Settings
st.subheader("Analysis Settings")
col_global1, col_global2 = st.columns(2)
with col_global1:
    grouping_option = st.selectbox(
        "Group measurements by:",
        options=['Sclin_mm', 'nominal_field_size_x_cm', 'nominal_field_size_y_cm'],
        format_func=lambda x: "Sclin (mm)" if x == 'Sclin_mm' else ("Nominal X" if x == 'nominal_field_size_x_cm' else "Nominal Y")
    )

with col_global2:
    recalc_acr = st.checkbox("Recalculate ACR globally")
    acr_value = 1.0
    if recalc_acr:
        acr_value = st.number_input('New ACR Value:', min_value=0.000, max_value=2.000, value=1.00, step=0.001, format="%.3f")

st.subheader("Measurement Sets")

if not st.session_state['measurement_sets']:
    add_measurement_set() # Ensure at least one

# Container for sets
for idx, dset in enumerate(st.session_state['measurement_sets']):
    with st.expander(f"Measurement Set: {dset['name']}", expanded=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            dset['files'] = st.multiselect(
                f"Select files for {dset['name']}",
                filenames,
                default=dset['files'],
                key=f"files_{dset['id']}"
            )
        with c2:
            dset['name'] = st.text_input("Legend Name", value=dset['name'], key=f"name_{dset['id']}")
        with c3:
            dset['color'] = st.color_picker("Color", value=dset['color'], key=f"color_{dset['id']}")

        # Reference Field Selection for this Set
        if dset['files']:
            full_paths = [os.path.join("Measurements", "OF_tables", f) for f in dset['files']]
            df_temp, _ = process_dataset(full_paths, grouping_option, acr_value if recalc_acr else None)

            if not df_temp.empty:
                # Create labels for formatting
                df_temp['ref_label'] = df_temp.apply(get_reference_label, axis=1)

                # Try to maintain selection if valid
                options = df_temp[grouping_option].tolist()
                labels = df_temp['ref_label'].tolist()

                # Map options to labels for selectbox
                option_map = dict(zip(options, labels))

                # Default to largest field (usually last)
                default_idx = len(options) - 1

                # Check if saved ref_value is still valid
                current_val = dset.get('ref_value')
                if current_val in options:
                    default_idx = options.index(current_val)

                selected_val = st.selectbox(
                    "Reference Field Size",
                    options=options,
                    index=default_idx,
                    format_func=lambda x: option_map.get(x, str(x)),
                    key=f"ref_{dset['id']}"
                )
                dset['ref_value'] = selected_val

        if idx > 0:
            if st.button("Remove Set", key=f"rem_{dset['id']}"):
                remove_measurement_set(idx)
                st.rerun()

if st.button("Add another Measurement Set"):
    add_measurement_set()
    st.rerun()

# --- Calculation & Plotting ---

fig1 = go.Figure()
comparison_data = {} # For the table: {SetName: {GroupingVal: OF}}
all_grouping_vals = set()

# Process all sets
valid_sets_count = 0

# Store grouped dfs for display
grouped_dfs_to_display = []

for dset in st.session_state['measurement_sets']:
    if not dset['files'] or dset['ref_value'] is None:
        continue

    full_paths = [os.path.join("Measurements", "OF_tables", f) for f in dset['files']]
    df_res, df_raw = process_dataset(full_paths, grouping_option, acr_value if recalc_acr else None)

    if df_res.empty:
        continue

    # Normalize
    ref_row = df_res[df_res[grouping_option] == dset['ref_value']]
    if ref_row.empty:
        continue # Should not happen if logic is correct

    ref_charge = ref_row.iloc[0]["charge_prop_dose_nC"]
    df_res["field_factor"] = df_res.charge_prop_dose_nC / ref_charge
    df_res["error_normalized"] = df_res.error / ref_charge

    # Plot
    fig1.add_trace(go.Scatter(
        x=df_res[grouping_option],
        y=df_res["field_factor"],
        mode='lines+markers',
        name=dset['name'],
        marker=dict(color=dset['color']),
        line=dict(color=dset['color']),
        error_y=dict(
            type='data',
            array=df_res['error_normalized'],
            visible=True
        )
    ))

    # Collect data for table
    comparison_data[dset['name']] = dict(zip(df_res[grouping_option], df_res["field_factor"]))
    all_grouping_vals.update(df_res[grouping_option].unique())

    grouped_dfs_to_display.append((dset['name'], df_res))
    valid_sets_count += 1


# --- External Sensors (Legacy Support) ---
# Allowing user to add manual curves as before, but maybe simplified or integrated as "Manual Set"
# Keeping original "sensor2" "sensor3" logic for now as requested features didn't explicitly say remove it,
# but "merged them all" complaint suggests we should prioritize the new clean approach.
# However, user said "Similar to how we can add external measurements... I want to be able to compare several different internal measurements".
# So I will keep the external sensor inputs below the main plot for extra comparisons.

with st.expander("Add External/Manual Sensors"):
    sensor2 = st.text_input('Name of sensor2', placeholder="Input name of sensor")
    if sensor2 != '':
        of_default_values = '1,0.966,0.944,0.895,0.767,0.687'
        nf_default_values = '25,12.5,10,7.5,5,4'
        of_and_nf_file_values = get_sensor_defaults(2)
        if of_and_nf_file_values is not None:
            of_default_values = of_and_nf_file_values[0]
            nf_default_values = of_and_nf_file_values[1]

        s2ofs = st.text_input('sensor2 OFs (separated by commas)', value = of_default_values)
        listsensor2 = s2ofs.split(',')
        listsensor2float = [float(i) for i in listsensor2]

        sensor2nominal_fields = st.text_input('sensor2 nominal_field sizes (separated by commas)', value = nf_default_values)
        listofsensor2nominal_fields = sensor2nominal_fields.split(',')
        listofsensor2nominal_fieldsfloat = [float(i) for i in listofsensor2nominal_fields]

        fig1.add_trace(go.Scatter(
            x = listofsensor2nominal_fieldsfloat,
            y = listsensor2float,
            mode = 'lines+markers',
            marker = dict(color = 'red', opacity = 0.5),
            line = dict(color = 'rgba(255, 0, 0, 0.5)'),
            name = sensor2
        ))

        # Add to table data
        # For manual sensors, we assume the X axis matches the current grouping preference (usually nominal if manual)
        comparison_data[sensor2] = dict(zip(listofsensor2nominal_fieldsfloat, listsensor2float))
        all_grouping_vals.update(listofsensor2nominal_fieldsfloat)

    sensor3 = st.text_input('Name of sensor3', placeholder="Input name of sensor")
    if sensor3 != '':
        of_default_values = '1,0.966,0.944,0.895,0.767,0.687'
        nf_default_values = '25,12.5,10,7.5,5,4'
        of_and_nf_file_values = get_sensor_defaults(3)
        if of_and_nf_file_values is not None:
            of_default_values = of_and_nf_file_values[0]
            nf_default_values = of_and_nf_file_values[1]
        else:
            st.warning("Error with Other Detectos OFs file")
        s3ofs = st.text_input('sensor3 OFs (separated by commas)', of_default_values)
        listsensor3 = s3ofs.split(',')
        listsensor3float = [float(i) for i in listsensor3]
        sensor3nominal_fields = st.text_input('sensor3 nominal_field sizes (separated by commas)',
                                              value=nf_default_values)
        listofsensor3nominal_fields = sensor3nominal_fields.split(',')
        listofsensor3nominal_fieldsfloat = [float(i) for i in listofsensor3nominal_fields]
        fig1.add_traces(
            go.Scatter(
                x=listofsensor3nominal_fieldsfloat,
                y=listsensor3float,
                mode='markers',
                marker=dict(color='green', opacity=0.5),
                name=sensor3
            )
        )

        # Add to table data
        # For manual sensors, we assume the X axis matches the current grouping preference (usually nominal if manual)
        comparison_data[sensor3] = dict(zip(listofsensor3nominal_fieldsfloat, listsensor3float))
        all_grouping_vals.update(listofsensor3nominal_fieldsfloat)

if valid_sets_count > 0:
    fig1.update_yaxes(title='OF')

    xlabel = "Sclin (mm)"
    if grouping_option == 'nominal_field_size_x_cm': xlabel = "Nominal Field Size X"
    if grouping_option == 'nominal_field_size_y_cm': xlabel = "Nominal Field Size Y"
    fig1.update_xaxes(title=xlabel)

    st.plotly_chart(fig1)

    # --- Comparison Table ---
    st.write("### Comparison Table")

    # Sort grouping values
    sorted_vals = sorted(list(all_grouping_vals), reverse=True)

    table_rows = []
    for val in sorted_vals:
        row = {'Field Size': val}
        for set_name, data_map in comparison_data.items():
            row[set_name] = data_map.get(val, None)
        table_rows.append(row)

    df_comparison = pd.DataFrame(table_rows)
    # Format columns
    st.dataframe(df_comparison.style.format(precision=4))

    st.write("---")
    st.write("### Data Details by Set")

    for name, df_grouped_set in grouped_dfs_to_display:
        st.write(f"#### {name}")

        # Prepare presentation dataframe
        # select columns if they exist
        cols_to_show = [
            "sensorcharge_nC",
            "cerenkovcharge_nC",
            "charge_prop_dose_nC",
            "center_x_mm",
            "center_y_mm",
            "field_size_x_mm",
            "field_size_y_mm",
            "nominal_field_size_x_cm",
            "nominal_field_size_y_cm",
            "Sclin_mm",
            "field_factor"
        ]

        # Filter to only columns present in df_grouped_set
        existing_cols = [c for c in cols_to_show if c in df_grouped_set.columns]
        df_display = df_grouped_set[existing_cols].copy()

        # Rename for nicer display
        rename_map = {
            "sensorcharge_nC": "Sensor Charge (nC)",
            "cerenkovcharge_nC": "Cerenkov Charge (nC)",
            "charge_prop_dose_nC": "Charge proportional to Dose (nC)",
            "center_x_mm": "Center X (mm)",
            "center_y_mm": "Center Y (mm)",
            "field_size_x_mm": "Field Size X (mm)",
            "field_size_y_mm": "Field Size Y (mm)",
            "nominal_field_size_x_cm": "Nominal X (cm)",
            "nominal_field_size_y_cm": "Nominal Y (cm)",
            "Sclin_mm": "Sclin (mm)",
            "field_factor": "Field Factor"
        }
        df_display = df_display.rename(columns=rename_map)

        st.dataframe(df_display)

else:
    st.info("Select files above to generate the plot.")

