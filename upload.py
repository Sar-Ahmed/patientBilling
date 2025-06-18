import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import re

# Configure Tesseract path for Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\tesseract.exe'

def extract_phns_from_text(text):
    # Find all 10-digit numbers (PHNs)
    phn_pattern = r'\b\d{10}\b'
    phns = re.findall(phn_pattern, text)
    return phns

def upload_file():
    st.title("Extract PHNs from PNG File and Match with Patient List")
    uploaded_file = st.file_uploader("Choose a PNG file", type=['png'])
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_container_width=True)
            raw_text = pytesseract.image_to_string(image)
            phns = extract_phns_from_text(raw_text)
            if phns:
                # Load Patient_List.csv
                try:
                    patient_df = pd.read_csv('Patient_List.csv', dtype=str)
                except Exception as e:
                    st.error(f"Could not load Patient_List.csv: {str(e)}")
                    return
                # Normalize column names to lower case for matching
                patient_df.columns = [col.lower() for col in patient_df.columns]
                # Check required columns
                required_cols = ['phn', 'first_name', 'last_name', 'date_of_birth', 'diagnosis']
                for col in required_cols:
                    if col not in patient_df.columns:
                        st.error(f"Column '{col}' not found in Patient_List.csv.")
                        return
                # Normalize PHN column in patient list
                patient_df['phn'] = patient_df['phn'].astype(str)
                # Match extracted PHNs with patient list
                match_results = []
                for phn in phns:
                    match_row = patient_df[patient_df['phn'] == phn]
                    if not match_row.empty:
                        patient_info = match_row.iloc[0].to_dict()
                        match_results.append({
                            'PHN': phn,
                            'Match': True,
                            'First Name': patient_info.get('first_name', ''),
                            'Last Name': patient_info.get('last_name', ''),
                            'Date of Birth': patient_info.get('date_of_birth', ''),
                            'Diagnosis': patient_info.get('diagnosis', '')
                        })
                    else:
                        match_results.append({
                            'PHN': phn,
                            'Match': False,
                            'First Name': '',
                            'Last Name': '',
                            'Date of Birth': '',
                            'Diagnosis': ''
                        })
                st.success(f"Found {len(phns)} PHN(s) in the image. See match results below:")
                st.dataframe(pd.DataFrame(match_results))
            else:
                st.error("No PHN found in the image.")
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")

if __name__ == "__main__":
    upload_file() 