import streamlit as st
import pandas as pd
import os
import glob
from datetime import datetime

# Constants
PATIENT_LIST_PATH = 'Patient_list.csv'
DIAGNOSIS_CODES_DIR = "diagnosis codes"
NEW_CODES_PATH = os.path.join(DIAGNOSIS_CODES_DIR, "Diagnosis Code - NEW.csv")

def load_patient_list():
    if os.path.exists(PATIENT_LIST_PATH):
        df = pd.read_csv(PATIENT_LIST_PATH, dtype={'PHN': str})
        if 'diagnosis' not in df.columns:
            df['diagnosis'] = ''
        return df
    else:
        return pd.DataFrame(columns=['PHN', 'last_name', 'first_name', 'date_of_birth', 'diagnosis'])

def load_diagnosis_codes():
    all_csv_paths = glob.glob(os.path.join(DIAGNOSIS_CODES_DIR, "*.csv"))
    diag_frames = []
    for path in all_csv_paths:
        df = pd.read_csv(path)
        if {'Code', 'Description'}.issubset(df.columns):
            diag_frames.append(df[['Code', 'Description']])
    if not diag_frames:
        st.error("No valid diagnosis files found.")
        st.stop()
    combined = pd.concat(diag_frames, ignore_index=True).dropna(subset=['Code']).drop_duplicates()
    return combined

def get_diag_options(diag_df):
    options = diag_df['Code'].astype(str) + " - " + diag_df['Description'].astype(str)
    return options

# Load data
patient_df = load_patient_list()
diag_df = load_diagnosis_codes()
diag_options = get_diag_options(diag_df)
diag_code_map = dict(zip(diag_options, diag_df['Code']))

# UI Setup
st.title("🩺 Patient Billing Entry (Live Preview)")

date_of_service = st.date_input("📅 Date of Service", value=datetime.today(), key="date_of_service")
facility_input = st.radio("🏥 Facility", [
    "A - OD096 (Academy Hill Medical)",
    "S - OD411 (Stone Bridge Clinic)"
], index=0, key="facility_input")

facility_code, rural_premium = ("OD096", "None") if facility_input.startswith("A") else ("OD411", "Big White")
location = "L"

if "num_patients" not in st.session_state:
    st.session_state.num_patients = 1
if "entries" not in st.session_state:
    st.session_state.entries = {}

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

for i in range(st.session_state.num_patients):
    st.markdown(f"---\n### Patient #{i + 1}")

    if f"add_new_{i}" not in st.session_state:
        st.session_state[f"add_new_{i}"] = False

    phn_display_list = [
        f"{row['PHN']} - {row['first_name']} {row['last_name']}"
        for _, row in patient_df.iterrows()
    ]
    phn_display_list = ["➕ Add New Patient"] + phn_display_list

    phn_selection = st.selectbox(f"Select or Add Patient #{i+1}", phn_display_list, key=f"phn_select_{i}")

    if phn_selection == "➕ Add New Patient":
        st.session_state[f"add_new_{i}"] = True
    else:
        st.session_state[f"add_new_{i}"] = False

    if st.session_state[f"add_new_{i}"]:
        col1, col2 = st.columns([4, 1])
        with col1:
            phn = st.text_input(f"New PHN #{i+1}", key=f"phn_{i}", value=st.session_state.get(f"phn_{i}_val", ""))
        with col2:
            if st.button(f"Clear PHN #{i+1}", key=f"clear_phn_btn_{i}"):
                phn = ""
                st.session_state[f"phn_{i}_val"] = phn
                st.rerun()
        st.session_state[f"phn_{i}_val"] = phn

        fname = st.text_input(f"First Name #{i+1}", key=f"fname_{i}", value=st.session_state.get(f"fname_{i}_val", ""))
        lname = st.text_input(f"Last Name #{i+1}", key=f"lname_{i}", value=st.session_state.get(f"lname_{i}_val", ""))
        dob = st.text_input(f"DOB #{i+1} (YYYY-MM-DD)", key=f"dob_{i}", value=st.session_state.get(f"dob_{i}_val", ""))

        st.session_state[f"fname_{i}_val"] = fname
        st.session_state[f"lname_{i}_val"] = lname
        st.session_state[f"dob_{i}_val"] = dob

        st.warning("New patient. Fill in all details.")
        existing = pd.DataFrame()
    else:
        phn = phn_selection.split(" - ")[0]
        existing = patient_df[patient_df['PHN'] == phn]
        if not existing.empty:
            patient = existing.iloc[0]
            st.success(f"Found: {patient['first_name']} {patient['last_name']}")
            fname = st.text_input(f"First Name #{i+1}", value=patient['first_name'], key=f"fname_{i}", disabled=True)
            lname = st.text_input(f"Last Name #{i+1}", value=patient['last_name'], key=f"lname_{i}", disabled=True)
            dob = st.text_input(f"DOB #{i+1} (YYYY-MM-DD)", value=patient['date_of_birth'], key=f"dob_{i}", disabled=True)
        else:
            st.warning("⚠️ Selected PHN not found. Please choose 'Add New Patient' to add.")
            fname = lname = dob = ""
            existing = pd.DataFrame()

    billing_item = st.selectbox(
        f"Billing Item #{i+1}",
        billing_keys,
        format_func=lambda code: f"{code} - {billing_options[code]}",
        index=billing_keys.index('98032'),
        key=f"billing_item_{i}"
    )

    saved_diag_code = existing.iloc[0]['diagnosis'] if not existing.empty else ""

    if billing_item in ['98010', '98011', '98012', '98119', '98990']:
        diagnosis_code = "L23"
        st.text_input(f"Diagnosis #{i+1}", "L23 - Automatically assigned", key=f"diag_{i}", disabled=True)
    else:
        diag_df = load_diagnosis_codes()
        diag_options = get_diag_options(diag_df)
        diag_code_map = dict(zip(diag_options, diag_df['Code']))

        diagnosis_choices = ["Select", "➕ Add New Diagnosis"] + list(diag_options)
        if pd.notna(saved_diag_code) and saved_diag_code != "" and not any(opt.startswith(str(saved_diag_code)) for opt in diagnosis_choices):
            diagnosis_choices.insert(1, saved_diag_code)

        default_index = next((idx for idx, option in enumerate(diagnosis_choices) if str(saved_diag_code).startswith(option.split(" - ")[0])), 0)

        diagnosis_selection = st.selectbox(f"Diagnosis #{i+1}", diagnosis_choices, key=f"diag_select_{i}", index=default_index)

        if diagnosis_selection == "➕ Add New Diagnosis":
            new_code = st.text_input(f"New Diagnosis Code #{i+1}", key=f"new_code_{i}", value=st.session_state.get(f"new_code_{i}", ""))
            new_desc = st.text_input(f"New Diagnosis Description #{i+1}", key=f"new_desc_{i}", value=st.session_state.get(f"new_desc_{i}", ""))
            diagnosis_code = ""
            if new_code.strip() and new_desc.strip():
                diagnosis_code = new_code.strip()
                diagnosis_selection = f"{diagnosis_code} - {new_desc.strip()}"
                if st.button(f"💾 Save Diagnosis for Patient #{i+1}", key=f"save_diag_btn_{i}"):
                    pd.DataFrame([{"Code": diagnosis_code, "Description": new_desc.strip()}]).to_csv(
                        NEW_CODES_PATH, mode='a', index=False, header=not os.path.exists(NEW_CODES_PATH))
                    st.success(f"Saved: {diagnosis_code} - {new_desc.strip()}")
                    st.session_state[f"new_code_{i}"] = ""
                    st.session_state[f"new_desc_{i}"] = ""
                    st.rerun()
            else:
                st.warning(f"⚠️ Enter both code and description for Patient #{i+1}.")
        else:
            diagnosis_code = diag_code_map.get(diagnosis_selection, "")
            if diagnosis_selection == "Select":
                st.warning(f"⚠️ Please select a diagnosis for Patient #{i+1}.")

    start_time = st.text_input(f"Start Time #{i+1} (HH:MM)", key=f"start_{i}") if billing_item in ['98010', '98011', '98012', '98119'] else ''
    end_time = st.text_input(f"End Time #{i+1} (HH:MM)", key=f"end_{i}") if billing_item in ['98010', '98011', '98012', '98119'] else ''

    if st.session_state[f"add_new_{i}"]:
        st.session_state[f"phn_{i}_val"] = phn
        st.session_state[f"fname_{i}_val"] = fname
        st.session_state[f"lname_{i}_val"] = lname
        st.session_state[f"dob_{i}_val"] = dob

    if phn:
        st.session_state.entries[i] = {
            'date_of_service': date_of_service.strftime('%Y-%m-%d'),
            'last_name': lname,
            'first_name': fname,
            'PHN': phn,
            'date_of_birth': dob,
            'billing_item': billing_item,
            'diagnosis': diagnosis_code,
            'location': location,
            'facility_code': facility_code,
            'start_time': start_time,
            'end_time': end_time,
            'rural_premium': rural_premium
        }

    if i == st.session_state.num_patients - 1:
        if st.button("➕ Add Another Patient", key=f"add_patient_{st.session_state.num_patients}"):
            st.session_state.num_patients += 1
            st.rerun()

if st.session_state.entries:
    st.subheader("📋 Live Preview")
    preview_df = pd.DataFrame(st.session_state.entries.values())
    st.dataframe(preview_df, use_container_width=True)

if st.button("💾 Save Patient List with Diagnosis"):
    updated_patients = patient_df.copy()
    for entry in st.session_state.entries.values():
        if not entry['PHN']:
            continue
        idx = updated_patients[updated_patients['PHN'] == entry['PHN']].index
        if not idx.empty:
            updated_patients.loc[idx[0], ['first_name', 'last_name', 'date_of_birth', 'diagnosis']] = (
                entry['first_name'], entry['last_name'], entry['date_of_birth'], entry['diagnosis']
            )
        else:
            updated_patients = pd.concat([updated_patients, pd.DataFrame([{
                'PHN': entry['PHN'],
                'first_name': entry['first_name'],
                'last_name': entry['last_name'],
                'date_of_birth': entry['date_of_birth'],
                'diagnosis': entry['diagnosis']
            }])], ignore_index=True)
    updated_patients.to_csv(PATIENT_LIST_PATH, index=False)
    st.success("✅ Patient list updated with diagnosis.")
