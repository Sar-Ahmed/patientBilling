import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re
import os
import glob
import datetime
import io
import csv

def repair_multiline_csv(file_path):
    """Read a CSV file and join lines that start with a comma to the previous line."""
    repaired_lines = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith(','):
                if repaired_lines:
                    repaired_lines[-1] = repaired_lines[-1].rstrip('\n') + ' ' + line.lstrip(',').strip('\n')
                else:
                    repaired_lines.append(line.lstrip(',').strip('\n'))
            else:
                repaired_lines.append(line.strip('\n'))
    return io.StringIO('\n'.join(repaired_lines))

def extract_visit_type(text):
    """Extract Visit Type from OCR text and map to billing code for LFP Virtual or LFP Office only."""
    if 'lfp virtual' in text.lower():
        return '98032'
    if 'lfp office' in text.lower():
        return '98031'
    return '98032'  # Default to LFP Virtual

def extract_phns_from_text(text):
    phn_pattern = r'\b\d{10}\b'
    phns = re.findall(phn_pattern, text)
    return phns

def extract_appointment_date(text):
    # Replace common OCR mistakes
    text = text.replace('O', '0').replace('o', '0')

    # Look for 'From:' date at the top (most reliable for your use case)
    from_match = re.search(r'From\s*:?\s*(20\d{2}-\d{2}-\d{2})', text, re.IGNORECASE)
    if from_match:
        date_str = from_match.group(1)
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            pass

    # Look for 8-digit date like 20280610
    compact_match = re.search(r'(20\d{2})(\d{2})(\d{2})', text)
    if compact_match:
        date_str = f"{compact_match.group(1)}-{compact_match.group(2)}-{compact_match.group(3)}"
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            pass

    # Fallback: find any valid YYYY-MM-DD in the text
    date_pattern = r'20\d{2}-\d{2}-\d{2}'
    dates = re.findall(date_pattern, text)
    for date_str in dates:
        try:
            datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            continue
    return None

def extract_diagnosis_code(searchable_text):
    """Extract just the diagnosis code from the searchable format 'Code - Description (Category)'"""
    # Handle NaN, None, or empty values
    if pd.isna(searchable_text) or searchable_text == '' or searchable_text is None:
        return ''
    
    # Convert to string to handle float values
    searchable_text = str(searchable_text)
    
    # Extract the code part before the first dash
    parts = searchable_text.split(' - ')
    if len(parts) > 0:
        return parts[0].strip()
    return searchable_text

def load_diagnosis_codes():
    """Load all diagnosis codes from CSV files in the diagnosis codes folder, repairing multi-line descriptions if needed."""
    all_codes = []
    diagnosis_folder = 'diagnosis codes'
    
    if os.path.exists(diagnosis_folder):
        # Get all CSV files in the diagnosis codes folder
        csv_files = glob.glob(os.path.join(diagnosis_folder, '*.csv'))
        
        for csv_file in csv_files:
            try:
                # Use the repair function to handle multi-line descriptions
                repaired_csv = repair_multiline_csv(csv_file)
                # Force Code column to be treated as string to prevent numeric conversion
                df = pd.read_csv(repaired_csv, dtype={'Code': str})
                # Check if the file has Code and Description columns
                if 'Code' in df.columns and 'Description' in df.columns:
                    # Clean the data - remove rows with NaN values
                    df = df.dropna(subset=['Code', 'Description'])
                    # Convert Code to string and handle any remaining NaN values
                    df['Code'] = df['Code'].astype(str).fillna('')
                    df['Description'] = df['Description'].fillna('')
                    # Add filename as category for organization
                    category = os.path.basename(csv_file).replace('.csv', '').replace('Diagnosis_Code_', '')
                    df['Category'] = category
                    all_codes.append(df)
            except Exception as e:
                st.warning(f"Could not load {csv_file}: {str(e)}")
    
    if all_codes:
        # Combine all dataframes
        combined_df = pd.concat(all_codes, ignore_index=True)
        # Additional cleaning - remove any rows with empty codes or descriptions
        combined_df = combined_df[
            (combined_df['Code'].str.strip() != '') & 
            (combined_df['Description'].str.strip() != '')
        ]
        # Create a searchable format: "Code - Description (Category)"
        combined_df['Searchable'] = combined_df['Code'].astype(str) + ' - ' + combined_df['Description'] + ' (' + combined_df['Category'] + ')'
        # Convert to list and ensure all values are strings
        searchable_list = combined_df['Searchable'].astype(str).tolist()
        return searchable_list
    else:
        return []

PATIENT_LIST_PATH = 'Patient_List.csv'

# Define facility codes from app.py
FACILITY_CODES = {
    'OD096': 'Academy Hill Medical',
    'OD411': 'Stone Bridge Clinic'
}

# Define billing codes from app.py
BILLING_CODES = {
    '98010': 'LFP Direct Patient Care',
    '98011': 'LFP Indirect Patient Care',
    '98012': 'LFP Admin Care',
    '98119': 'Travel Time',
    '98031': 'LFP Office',
    '98990': 'Primary Care Panel',
    '98032': 'LFP Virtual (default)'
}

# Define billing codes that should set diagnosis to L23
L23_BILLING_CODES = ['98010', '98011', '98012', '98119', '98990']

# Define billing codes that require start/end time input
TIME_REQUIRED_CODES = ['98119', '98010', '98011', '98012']

def load_patient_list():
    if os.path.exists(PATIENT_LIST_PATH):
        df = pd.read_csv(PATIENT_LIST_PATH, dtype={'PHN': str})
        if 'diagnosis' not in df.columns:
            df['diagnosis'] = ''
        return df
    else:
        return pd.DataFrame(columns=['PHN', 'last_name', 'first_name', 'date_of_birth', 'diagnosis'])

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\tesseract.exe'

# Load diagnosis codes
diagnosis_codes_df = load_diagnosis_codes()

# Add facility code selection
facility_code = st.selectbox(
    "Select Facility Code",
    options=list(FACILITY_CODES.keys()),
    format_func=lambda x: f"{x} - {FACILITY_CODES[x]}",
    help="Select the facility code for the location"
)

# Automatically set Rural Premium based on facility code
if facility_code == 'OD411':
    rural_premium = 'Big White'
elif facility_code == 'OD096':
    rural_premium = 'None'

uploaded_png = st.file_uploader("Upload a PNG screenshot to extract PHNs and autofill patient info", type=["png"], key="phn_png_upload")

if uploaded_png is not None:
    try:
        image = Image.open(uploaded_png)
        st.image(image, caption="Uploaded Image", use_container_width=True)
        raw_text = pytesseract.image_to_string(image)
        
        # Extract appointment date from the image
        appointment_date = extract_appointment_date(raw_text)
        # Extract visit type from the image
        visit_type_code = extract_visit_type(raw_text)
        if appointment_date:
            st.info(f"Found appointment date in image: {appointment_date}")
        if visit_type_code:
            st.info(f"Found visit type in image: {BILLING_CODES[visit_type_code]} (Billing Code: {visit_type_code})")
        
        phns = extract_phns_from_text(raw_text)
        if phns:
            patient_df = load_patient_list()
            # Normalize columns for matching
            patient_df.columns = [col.lower() for col in patient_df.columns]
            patient_df['phn'] = patient_df['phn'].astype(str)
            results = []
            for phn in phns:
                match_row = patient_df[patient_df['phn'] == phn]
                billing_code = visit_type_code if visit_type_code else '98032'  # Use visit type if found, else default
                if not match_row.empty:
                    patient_info = match_row.iloc[0].to_dict()
                    results.append({
                        'date_of_service': appointment_date if appointment_date else 'Not found in image',
                        'last_name': patient_info.get('last_name', ''),
                        'first_name': patient_info.get('first_name', ''),
                        'PHN': phn,
                        'date_of_birth': patient_info.get('date_of_birth', ''),
                        'billing_item': billing_code,
                        'diagnosis': patient_info.get('diagnosis', ''),
                        'location': 'L',
                        'facility_code': facility_code,
                        'start_time': '',
                        'end_time': '',
                        'rural_premium': rural_premium
                    })
                else:
                    results.append({
                        'date_of_service': appointment_date if appointment_date else 'Not found in image',
                        'last_name': '',
                        'first_name': '',
                        'PHN': phn,
                        'date_of_birth': '',
                        'billing_item': billing_code,
                        'diagnosis': '',
                        'location': 'L',
                        'facility_code': facility_code,
                        'start_time': '',
                        'end_time': '',
                        'rural_premium': rural_premium
                    })
            st.success(f"Found {len(phns)} PHN(s) in the image. See autofilled info below:")
            
            # Initialize session state for the dataframe if it doesn't exist
            if 'df' not in st.session_state:
                st.session_state.df = pd.DataFrame(results)
                
                # Add 4 duplicate rows with specific billing codes for the first row
                if len(results) > 0:
                    first_row = results[0].copy()
                    additional_billing_codes = ['98011', '98012', '98010', '98119']
                    
                    for billing_code in additional_billing_codes:
                        duplicate_row = first_row.copy()
                        duplicate_row['billing_item'] = billing_code
                        duplicate_row['diagnosis'] = 'L23'
                        duplicate_row['start_time'] = ''
                        duplicate_row['end_time'] = ''
                        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([duplicate_row])], ignore_index=True)
            
            # Update Location column if facility code changed
            if not st.session_state.df.empty:
                st.session_state.df['facility_code'] = facility_code
                st.session_state.df['rural_premium'] = rural_premium
                st.session_state.df['location'] = 'L'
            
            # Create a copy of the current dataframe
            current_df = st.session_state.df.copy()
            
            # Add a duplicate button for each row
            for idx in range(len(current_df)):
                st.markdown(f"---")
                st.markdown(f"**Row {idx + 1}**")
                
                col1, col2 = st.columns([0.95, 0.05])
                with col1:
                    # Check if this is a new patient (no first name)
                    is_new_patient = not current_df.iloc[idx]['first_name']
                    
                    if is_new_patient:
                        st.warning(f"Patient with PHN {current_df.iloc[idx]['PHN']} not found in database. Please add patient information.")
                        with st.expander("Add Patient Information", expanded=True):
                            # Load patient list for dropdown
                            patient_df_dropdown = load_patient_list()
                            phn_options = ["➕ Enter New PHN"]
                            phn_display_map = {}
                            for _, row in patient_df_dropdown.iterrows():
                                display = f"{row['PHN']} - {row['first_name']} {row['last_name']}"
                                phn_options.append(display)
                                phn_display_map[display] = row
                            phn_value = current_df.iloc[idx]['PHN']
                            default_phn_option = 0
                            if phn_value:
                                for i, display in enumerate(phn_options):
                                    if display.startswith(phn_value):
                                        default_phn_option = i
                                        break
                            selected_phn_option = st.selectbox(
                                "Select Existing PHN or Enter New",
                                phn_options,
                                index=default_phn_option,
                                key=f"phn_select_{idx}"
                            )
                            if selected_phn_option == "➕ Enter New PHN":
                                st.warning("Patient with PHN not found in database. Please add patient information.")
                                phn_value = st.text_input("PHN (10 digits)", value=phn_value, key=f"phn_{idx}")
                                first_name = st.text_input("First Name", key=f"first_name_{idx}")
                                last_name = st.text_input("Last Name", key=f"last_name_{idx}")
                                date_of_birth = st.text_input("Date of Birth (YYYY-MM-DD)", key=f"dob_{idx}")
                                if st.button("Save Patient Info", key=f"save_patient_{idx}"):
                                    # Save to session state
                                    st.session_state.df.at[idx, 'PHN'] = phn_value
                                    st.session_state.df.at[idx, 'first_name'] = first_name
                                    st.session_state.df.at[idx, 'last_name'] = last_name
                                    st.session_state.df.at[idx, 'date_of_birth'] = date_of_birth
                                    # Only save to Patient_List.csv if it's a new PHN
                                    try:
                                        patient_df = load_patient_list()
                                        if not (patient_df['PHN'] == phn_value).any():
                                            new_patient = {
                                                'PHN': phn_value,
                                                'last_name': last_name,
                                                'first_name': first_name,
                                                'date_of_birth': date_of_birth,
                                                'diagnosis': ''
                                            }
                                            patient_df = pd.concat([patient_df, pd.DataFrame([new_patient])], ignore_index=True)
                                            patient_df.to_csv(PATIENT_LIST_PATH, index=False)
                                            st.success(f"Patient information saved to {PATIENT_LIST_PATH}")
                                    except Exception as e:
                                        st.error(f"Error saving to Patient_List.csv: {str(e)}")
                                    st.rerun()
                            else:
                                # Autofill from patient list and update session state immediately
                                selected_row = phn_display_map[selected_phn_option]
                                phn_value = selected_row['PHN']
                                first_name = selected_row['first_name']
                                last_name = selected_row['last_name']
                                date_of_birth = selected_row['date_of_birth']
                                st.session_state.df.at[idx, 'PHN'] = phn_value
                                st.session_state.df.at[idx, 'first_name'] = first_name
                                st.session_state.df.at[idx, 'last_name'] = last_name
                                st.session_state.df.at[idx, 'date_of_birth'] = date_of_birth
                    
                    # Create a more stable editing interface
                    row_data = current_df.iloc[idx]
                    
                    # Display current values
                    st.markdown("**Current Values:**")
                    st.info(f"**PHN:** {row_data['PHN']} | **Name:** {row_data['first_name']} {row_data['last_name']}")
                    
                    # Editable fields
                    st.markdown("**Edit Fields:**")
                    # --- Editable appointment date (text input and calendar picker) ---
                    import datetime
                    date_val = row_data['date_of_service']
                    try:
                        date_val = datetime.datetime.strptime(date_val, "%Y-%m-%d").date() if date_val else datetime.date.today()
                    except Exception:
                        date_val = datetime.date.today()
                    date_of_service_picker = st.date_input(
                        "Date of Service (calendar)",
                        value=date_val,
                        key=f"date_of_service_picker_{idx}"
                    )
                    # Save as string in YYYY-MM-DD format
                    date_of_service_str = date_of_service_picker.strftime("%Y-%m-%d")
                    # Also allow manual text input
                    date_of_service_text = st.text_input(
                        "Date of Service (YYYY-MM-DD)",
                        value=date_of_service_str,
                        key=f"date_of_service_text_{idx}"
                    )
                    # If either input changes, update session state
                    if date_of_service_text != row_data['date_of_service']:
                        st.session_state.df.at[idx, 'date_of_service'] = date_of_service_text
                    elif date_of_service_str != row_data['date_of_service']:
                        st.session_state.df.at[idx, 'date_of_service'] = date_of_service_str
                    
                    edit_col1, edit_col2 = st.columns(2)
                    
                    with edit_col1:
                        # Billing code selection with descriptions
                        billing_options = [f"{code} - {desc}" for code, desc in BILLING_CODES.items()]
                        current_billing_with_desc = f"{row_data['billing_item']} - {BILLING_CODES.get(row_data['billing_item'], '')}"
                        
                        new_billing_with_desc = st.selectbox(
                            "Billing Code",
                            options=billing_options,
                            index=billing_options.index(current_billing_with_desc) if current_billing_with_desc in billing_options else 0,
                            key=f"billing_{idx}",
                            help="Select the billing code for this service"
                        )
                        
                        # Extract just the billing code from the selection
                        new_billing_code = new_billing_with_desc.split(' - ')[0]
                        
                        # Update billing code in session state
                        if new_billing_code != row_data['billing_item']:
                            st.session_state.df.at[idx, 'billing_item'] = new_billing_code
                            # Auto-set L23 diagnosis for specific billing codes if diagnosis is empty
                            if new_billing_code in L23_BILLING_CODES and row_data['diagnosis'] == '':
                                st.session_state.df.at[idx, 'diagnosis'] = 'L23'
                    
                    with edit_col2:
                        # Diagnosis selection - only show for billing codes that don't auto-set to L23
                        current_diagnosis = row_data['diagnosis']
                        
                        if new_billing_code in L23_BILLING_CODES:
                            # Automatically set L23 for these billing codes
                            st.session_state.df.at[idx, 'diagnosis'] = 'L23'
                            st.info(f"✅ **Diagnosis automatically set to L23 for billing code {new_billing_code}**")
                        else:
                            # Find the matching diagnosis option
                            diagnosis_options = diagnosis_codes_df if isinstance(diagnosis_codes_df, list) else []
                            current_diagnosis_option = None
                            
                            if current_diagnosis:
                                # Try to find the current diagnosis in the options
                                for option in diagnosis_options:
                                    if option.startswith(f"{current_diagnosis} -"):
                                        current_diagnosis_option = option
                                        break
                            
                            new_diagnosis = st.selectbox(
                                "Diagnosis",
                                options=[''] + diagnosis_options,
                                index=diagnosis_options.index(current_diagnosis_option) + 1 if current_diagnosis_option else 0,
                                key=f"diagnosis_{idx}",
                                help="Select or search for a diagnosis code"
                            )
                            
                            # Add UI to add a new diagnosis code
                            with st.expander("➕ Add New Diagnosis Code", expanded=False):
                                new_code = st.text_input("New Diagnosis Code", key=f"new_diag_code_{idx}")
                                new_desc = st.text_input("New Diagnosis Description", key=f"new_diag_desc_{idx}")
                                if st.button("Add Diagnosis Code", key=f"add_diag_btn_{idx}"):
                                    if new_code and new_desc:
                                        # Append to Diagnosis_Code_NEW.csv
                                        new_row = [new_code, new_desc]
                                        new_csv_path = os.path.join('diagnosis codes', 'Diagnosis_Code_NEW.csv')
                                        try:
                                            # Check if file exists and if code already exists
                                            exists = os.path.exists(new_csv_path)
                                            code_exists = False
                                            if exists:
                                                with open(new_csv_path, 'r', encoding='utf-8') as f:
                                                    reader = csv.reader(f)
                                                    next(reader, None)  # skip header
                                                    for row in reader:
                                                        if row and row[0].strip() == new_code.strip():
                                                            code_exists = True
                                                            break
                                            if code_exists:
                                                st.warning(f"Code {new_code} already exists in Diagnosis_Code_NEW.csv.")
                                            else:
                                                with open(new_csv_path, 'a', encoding='utf-8', newline='') as f:
                                                    writer = csv.writer(f)
                                                    if not exists or os.path.getsize(new_csv_path) == 0:
                                                        writer.writerow(["Code", "Description"])
                                                    writer.writerow(new_row)
                                                st.success(f"Added new diagnosis code: {new_code} - {new_desc}")
                                                # Reload diagnosis codes
                                                diagnosis_codes_df = load_diagnosis_codes()
                                                st.rerun()
                                        except Exception as e:
                                            st.error(f"Error adding new diagnosis code: {str(e)}")
                                    else:
                                        st.warning("Please enter both a code and a description.")
                            
                            # Update diagnosis in session state
                            if new_diagnosis != current_diagnosis_option:
                                diagnosis_code = extract_diagnosis_code(new_diagnosis)
                                st.session_state.df.at[idx, 'diagnosis'] = diagnosis_code
                    
                    # Start/End time input for specific billing codes
                    if new_billing_code in TIME_REQUIRED_CODES:
                        st.info(f"⏰ **Billing code {new_billing_code} requires start and end times**")
                        time_col1, time_col2 = st.columns(2)
                        with time_col1:
                            start_time = st.text_input(
                                "Start Time (HH:MM)",
                                value=row_data['start_time'],
                                key=f"start_time_{idx}",
                                help="Enter start time in HH:MM format (e.g., 09:30)"
                            )
                            if start_time != row_data['start_time']:
                                st.session_state.df.at[idx, 'start_time'] = start_time
                        with time_col2:
                            end_time = st.text_input(
                                "End Time (HH:MM)",
                                value=row_data['end_time'],
                                key=f"end_time_{idx}",
                                help="Enter end time in HH:MM format (e.g., 10:30)"
                            )
                            if end_time != row_data['end_time']:
                                st.session_state.df.at[idx, 'end_time'] = end_time
                
                with col2:
                    if st.button("📋", key=f"duplicate_{idx}", help="Duplicate this row"):
                        # Get the current row data
                        row_data = st.session_state.df.iloc[idx].to_dict()
                        
                        # Clear billing code and diagnosis in the duplicated row
                        row_data['billing_item'] = '98032'  # Reset to default
                        row_data['diagnosis'] = ''  # Clear diagnosis
                        
                        # Insert the duplicated row right after the current row
                        before_rows = st.session_state.df.iloc[:idx+1]
                        after_rows = st.session_state.df.iloc[idx+1:]
                        new_row_df = pd.DataFrame([row_data])
                        
                        st.session_state.df = pd.concat([before_rows, new_row_df, after_rows], ignore_index=True)
                        st.rerun()
                    
                    if st.button("🗑️", key=f"delete_{idx}", help="Delete this row"):
                        # Remove the row at the current index
                        st.session_state.df = st.session_state.df.drop(index=idx).reset_index(drop=True)
                        st.rerun()
            
            # Add a button to add a new empty row
            if st.button("➕ Add New Row"):
                empty_row = {
                    'date_of_service': '',
                    'last_name': '',
                    'first_name': '',
                    'PHN': '',
                    'date_of_birth': '',
                    'billing_item': '98032',  # Default to LFP Virtual
                    'diagnosis': '',
                    'location': 'L',
                    'facility_code': facility_code,
                    'start_time': '',
                    'end_time': '',
                    'rural_premium': rural_premium
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([empty_row])], ignore_index=True)
                st.rerun()
            
            # Add a button to clear all rows
            if st.button("🗑️ Clear All Rows"):
                st.session_state.df = pd.DataFrame(columns=['date_of_service', 'last_name', 'first_name', 'PHN', 'date_of_birth', 'billing_item', 'diagnosis', 'location', 'facility_code', 'start_time', 'end_time', 'rural_premium'])
                st.rerun()
            
            # Add a button to save all patient rows (with diagnosis) to Patient_List.csv
            if st.button("💾 Save Patient List with Diagnosis"):
                updated_patients = load_patient_list()
                for _, entry in st.session_state.df.iterrows():
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
            
            # Display final summary table
            st.header("📊 Final Summary Table")
            st.dataframe(
                st.session_state.df,
                use_container_width=True,
                column_config={
                    "date_of_service": st.column_config.TextColumn(
                        "Date of Service",
                        help="Date of service in YYYY-MM-DD format",
                    ),
                    "last_name": st.column_config.TextColumn(
                        "Last Name",
                        help="Patient's last name",
                    ),
                    "first_name": st.column_config.TextColumn(
                        "First Name",
                        help="Patient's first name",
                    ),
                    "PHN": st.column_config.TextColumn(
                        "PHN",
                        help="Personal Health Number",
                    ),
                    "date_of_birth": st.column_config.TextColumn(
                        "Date of Birth",
                        help="Patient's date of birth",
                    ),
                    "billing_item": st.column_config.TextColumn(
                        "Billing Code",
                        help="Billing code for the service",
                    ),
                    "diagnosis": st.column_config.TextColumn(
                        "Diagnosis",
                        help="Patient diagnosis code and description",
                    ),
                    "location": st.column_config.TextColumn(
                        "Location Code",
                        help="Location code for the location",
                    ),
                    "facility_code": st.column_config.TextColumn(
                        "Facility Code",
                        help="Facility code for the location",
                    ),
                    "start_time": st.column_config.TextColumn(
                        "Start Time",
                        help="Start time of the appointment",
                    ),
                    "end_time": st.column_config.TextColumn(
                        "End Time",
                        help="End time of the appointment",
                    ),
                    "rural_premium": st.column_config.TextColumn(
                        "Rural Premium",
                        help="Rural premium for the location (automatically set based on facility)",
                    ),
                }
            )
            
            st.text_area("OCR Extracted Text (for debugging)", raw_text, height=200)
            
        else:
            st.error("No PHN found in the image.")
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")

