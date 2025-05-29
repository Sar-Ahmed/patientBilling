import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

# Constants
PATIENT_LIST_PATH = 'Patient_list.csv'
DIAGNOSIS_CODES_DIR = "diagnosis codes"

# Load patient list
if os.path.exists(PATIENT_LIST_PATH):
    patient_df = pd.read_csv(PATIENT_LIST_PATH, dtype={'PHN': str})
    if 'diagnosis' not in patient_df.columns:
        patient_df['diagnosis'] = ''
else:
    patient_df = pd.DataFrame(columns=['PHN', 'last_name', 'first_name', 'date_of_birth', 'diagnosis'])

# Load diagnosis codes
all_csv_paths = glob.glob(os.path.join(DIAGNOSIS_CODES_DIR, "*.csv"))
diag_frames = []
for path in all_csv_paths:
    df = pd.read_csv(path)
    if {'Code', 'Description'}.issubset(df.columns):
        diag_frames.append(df[['Code', 'Description']])

if not diag_frames:
    st.error("No valid diagnosis files found.")
    st.stop()

diag_df = pd.concat(diag_frames, ignore_index=True).dropna(subset=['Code']).drop_duplicates()
diag_options = diag_df['Code'].astype(str) + " - " + diag_df['Description'].astype(str)
diag_code_map = dict(zip(diag_options, diag_df['Code']))

# Page UI
st.title("🩺 Patient Billing Entry (Live Preview)")

date_of_service = st.date_input("📅 Date of Service", value=datetime.today())
facility_input = st.radio("🏥 Facility", [
    "A - OD096 (Academy Hill Medical)",
    "S - OD411 (Stone Bridge Clinic)"
], index=0)

facility_code, rural_premium = ("OD096", "None") if facility_input.startswith("A") else ("OD411", "Big White")
location = "L"

num_rows = st.number_input("👥 Number of Patients to Enter", min_value=1, value=1, step=1)

billing_options = {
    '98010': 'LFP Direct Patient Care',
    '98011': 'LFP Indirect Patient Care',
    '98012': 'LFP Admin Care',
    '98119': 'Travel Time',
    '98031': 'LFP Office',
    '98990': 'Primary Care Panel',
    '98032': 'LFP Virtual (default)'
}
billing_keys = list(billing_options.keys())

entries = []

# Dynamic form for each patient
for i in range(num_rows):
    st.markdown(f"---\n### Patient #{i + 1}")
    phn = st.text_input(f"PHN #{i+1}", key=f"phn_{i}").strip()
    existing = patient_df[patient_df['PHN'] == phn]

    if not existing.empty:
        patient = existing.iloc[0]
        st.success(f"Found: {patient['first_name']} {patient['last_name']}")
        fname = st.text_input(f"First Name #{i+1}", value=patient['first_name'], key=f"fname_{i}")
        lname = st.text_input(f"Last Name #{i+1}", value=patient['last_name'], key=f"lname_{i}")
        dob = st.text_input(f"DOB #{i+1} (YYYY-MM-DD)", value=patient['date_of_birth'], key=f"dob_{i}")
    else:
        st.warning("New patient")
        fname = st.text_input(f"First Name #{i+1}", key=f"fname_{i}")
        lname = st.text_input(f"Last Name #{i+1}", key=f"lname_{i}")
        dob = st.text_input(f"DOB #{i+1} (YYYY-MM-DD)", key=f"dob_{i}")

    billing_default_index = billing_keys.index('98032')
    billing_item = st.selectbox(
        f"Billing Item #{i+1}",
        billing_keys,
        format_func=lambda code: f"{code} - {billing_options[code]}",
        index=billing_default_index,
        key=f"billing_{i}"
    )
    
    NEW_CODES_PATH = os.path.join(DIAGNOSIS_CODES_DIR, "Diagnosis Code - NEW.csv")

    # Diagnosis logic with "Add New" option
    if billing_item in ['98010', '98011', '98012', '98119', '98990']:
        diagnosis_selection = "L23 - Automatically assigned"
        st.text_input(f"Diagnosis #{i+1}", diagnosis_selection, key=f"diag_{i}", disabled=True)
        diagnosis_code = "L23"
    else:
        diagnosis_choices = [""] + list(diag_options) + ["➕ Add New Diagnosis"]
        diagnosis_selection = st.selectbox(
            f"Diagnosis #{i+1}",
            diagnosis_choices,
            key=f"diag_{i}"
        )

        if diagnosis_selection == "➕ Add New Diagnosis":
            new_code = st.text_input(f"New Diagnosis Code #{i+1}", key=f"new_code_{i}")
            new_desc = st.text_input(f"New Diagnosis Description #{i+1}", key=f"new_desc_{i}")

            if new_code and new_desc:
                diagnosis_code = new_code.strip()
                diagnosis_selection = f"{diagnosis_code} - {new_desc.strip()}"

                if st.button(f"💾 Save Diagnosis for Patient #{i+1}", key=f"save_diag_{i}"):
                    new_entry = pd.DataFrame([{
                        "Code": diagnosis_code,
                        "Description": new_desc.strip()
                    }])

                    # Append or create new CSV file
                    write_header = not os.path.exists(NEW_CODES_PATH)
                    new_entry.to_csv(NEW_CODES_PATH, mode='a', index=False, header=write_header)

                    st.success(f"Saved: {diagnosis_code} - {new_desc.strip()}")

            else:
                diagnosis_code = ""
                st.warning(f"⚠️ Enter both code and description for Patient #{i+1}.")
        else:
            diagnosis_code = diag_code_map.get(diagnosis_selection, "")
            if diagnosis_selection == "":
                st.warning(f"⚠️ Please select a diagnosis for Patient #{i+1}.")



    # Start/End time logic
    if billing_item in ['98010', '98011', '98012', '98119']:
        start_time = st.text_input(f"Start Time #{i+1} (HH:MM)", key=f"start_{i}")
        end_time = st.text_input(f"End Time #{i+1} (HH:MM)", key=f"end_{i}")
    else:
        start_time = ''
        end_time = ''

    final_diagnosis = diagnosis_code

    entries.append({
        'date_of_service': date_of_service.strftime('%Y-%m-%d'),
        'last_name': lname,
        'first_name': fname,
        'PHN': phn,
        'date_of_birth': dob,
        'billing_item': billing_item,
        'diagnosis': final_diagnosis,
        'location': location,
        'facility_code': facility_code,
        'start_time': start_time,
        'end_time': end_time,
        'rural_premium': rural_premium
    })

# Live-updating preview
if entries:
    st.subheader("📋 Live Preview")
    preview_df = pd.DataFrame(entries)
    st.dataframe(preview_df, use_container_width=True)
