import streamlit as st
import pandas as pd
import os
from datetime import datetime

PATIENT_LIST_PATH = 'Patient_list.csv'

# Load patient list
if os.path.exists(PATIENT_LIST_PATH):
    patient_df = pd.read_csv(PATIENT_LIST_PATH)
    if 'diagnosis' not in patient_df.columns:
        patient_df['diagnosis'] = ''
else:
    patient_df = pd.DataFrame(columns=['PHN', 'last_name', 'first_name', 'date_of_birth', 'diagnosis'])

st.title("🩺 Patient Billing Entry")

# Date and Facility
date_of_service = st.date_input("📅 Date of Service", value=datetime.today())
facility_input = st.radio(
    "🏥 Facility",
    ["A - OD096 (Academy Hill Medical)", "S - OD411 (Stone Bridge Clinic)"],
    index=0  # Default to Academy Hill
)
facility_code, rural_premium = ("OD096", "None") if facility_input.startswith("A") else ("OD411", "Big White")
location = "L"

num_rows = st.number_input("👥 Number of Patients to Enter", min_value=1, value=1, step=1)

# Billing options
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

with st.form("entry_form"):
    for i in range(num_rows):
        st.markdown(f"---\n### Patient #{i+1}")

        phn = st.text_input(f"PHN #{i+1}", key=f"phn_{i}").strip()

        existing = patient_df[patient_df['PHN'] == phn]
        is_existing = not existing.empty

        if is_existing:
            existing_data = existing.iloc[0]
            st.success(f"Patient found: {existing_data['first_name']} {existing_data['last_name']}")
            first_name = st.text_input(f"First Name #{i+1}", value=existing_data['first_name'], key=f"fname_{i}")
            last_name = st.text_input(f"Last Name #{i+1}", value=existing_data['last_name'], key=f"lname_{i}")
            dob = st.text_input(f"DOB #{i+1} (YYYY-MM-DD)", value=existing_data['date_of_birth'], key=f"dob_{i}")
            diagnosis_default = existing_data['diagnosis']
        else:
            st.warning("New patient - please enter full details.")
            first_name = st.text_input(f"First Name #{i+1}", key=f"fname_{i}")
            last_name = st.text_input(f"Last Name #{i+1}", key=f"lname_{i}")
            dob = st.text_input(f"DOB #{i+1} (YYYY-MM-DD)", key=f"dob_{i}")
            diagnosis_default = ''

        billing_default_index = billing_keys.index('98032') if i == 0 else 0
        billing_item = st.selectbox(
            f"Billing Item #{i+1}",
            options=billing_keys,
            format_func=lambda code: f"{code} - {billing_options[code]}",
            index=billing_default_index,
            key=f"billing_{i}"
        )

        # Diagnosis input - just a text input, initialized with default diagnosis if any
        diagnosis = st.text_input(f"Diagnosis #{i+1}", value=diagnosis_default, key=f"diag_{i}")

        if billing_item in ['98010', '98011', '98012', '98119']:
            start_time = st.text_input(f"Start Time #{i+1} (HH:MM)", key=f"start_{i}")
            end_time = st.text_input(f"End Time #{i+1} (HH:MM)", key=f"end_{i}")
        else:
            start_time = ''
            end_time = ''

        entries.append({
            'PHN': phn,
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': dob,
            'billing_item': billing_item,
            'diagnosis': diagnosis,
            'start_time': start_time,
            'end_time': end_time
        })

    submitted = st.form_submit_button("💾 Save and Generate Records")

if submitted:
    # After submit, update diagnosis codes based on billing item rules
    for e in entries:
        if e['billing_item'] in ['98010', '98011', '98012', '98119', '98990']:
            e['diagnosis'] = "L23"  # Override diagnosis

    # Update or append patients in patient_df
    for e in entries:
        if e['PHN'] not in patient_df['PHN'].values:
            new_row = pd.DataFrame([{
                'PHN': e['PHN'],
                'first_name': e['first_name'],
                'last_name': e['last_name'],
                'date_of_birth': e['date_of_birth'],
                'diagnosis': e['diagnosis']
            }])
            patient_df = pd.concat([patient_df, new_row], ignore_index=True)
        else:
            patient_df.loc[patient_df['PHN'] == e['PHN'], 'diagnosis'] = e['diagnosis']

    patient_df.to_csv(PATIENT_LIST_PATH, index=False)
    st.success(f"✅ Patient list updated in `{PATIENT_LIST_PATH}`")

    service_df = pd.DataFrame({
        'date_of_service': [date_of_service.strftime('%Y-%m-%d')] * len(entries),
        'last_name': [e['last_name'] for e in entries],
        'first_name': [e['first_name'] for e in entries],
        'PHN': [e['PHN'] for e in entries],
        'date_of_birth': [e['date_of_birth'] for e in entries],
        'billing_item': [e['billing_item'] for e in entries],
        'diagnosis': [e['diagnosis'] for e in entries],
        'location': [location] * len(entries),
        'facility_code': [facility_code] * len(entries),
        'start_time': [e['start_time'] for e in entries],
        'end_time': [e['end_time'] for e in entries],
        'rural_premium': [rural_premium] * len(entries),
    })

    st.subheader("📋 Generated Service Records")
    st.dataframe(service_df)

    output_file = f"service_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    service_df.to_csv(output_file, index=False)
    st.success(f"💾 Service records saved to `{output_file}`")
