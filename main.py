import pandas as pd
import os

def main():
    # Load or create patient list
    patient_list_path = 'Patient_list.csv'
    if os.path.exists(patient_list_path):
        patient_df = pd.read_csv(patient_list_path)
        if 'diagnosis' not in patient_df.columns:
            patient_df['diagnosis'] = ''
    else:
        patient_df = pd.DataFrame(columns=['PHN', 'last_name', 'first_name', 'date_of_birth', 'diagnosis'])

    # Ask user for number of rows
    while True:
        try:
            num_rows = int(input("Enter the number of rows to generate: "))
            if num_rows > 0:
                break
            else:
                print("Please enter a positive integer.")
        except ValueError:
            print("Please enter a valid integer.")

    # Get common values
    print("\nEnter common values for all rows:")
    date_of_service = input("Date of service (YYYY-MM-DD): ")

    # Facility code input with simple codes
    while True:
        facility_mapping = {
            'S': ('OD411', 'Stone Bridge Clinic', 'Big White'),
            'A': ('OD096', 'Academy Hill Medical', 'None')
        }

        facility_input = input("Facility code (Enter 'S' for OD411 or 'A' for OD096): ").upper()

        if facility_input in facility_mapping:
            facility_code, facility_name, rural_premium = facility_mapping[facility_input]
            print(f"Added {facility_name} with Rural Premium as {rural_premium if rural_premium else 'None'}")
            break
        else:
            print("Invalid input. Please enter 'S' for OD411 or 'A' for OD096.")

    location = "L"

    # Initialize lists
    last_name_list = []
    first_name_list = []
    phn_list = []
    dob_list = []
    billing_item_list = []
    diagnosis_list = []
    start_time_list = []
    end_time_list = []

    print("\nEnter patient details for each row:")
    for i in range(1, num_rows + 1):
        print(f"\nRow {i}:")

        # PHN lookup
        while True:
            phn = input("PHN: ").strip()
            if not phn:
                print("PHN cannot be empty. Please try again.")
                continue

            patient_match = patient_df[patient_df['PHN'] == phn]
            if not patient_match.empty:
                # Existing patient
                patient = patient_match.iloc[0]
                print(f"Found existing patient: {patient['first_name']} {patient['last_name']}")
                last_name = patient['last_name']
                first_name = patient['first_name']
                dob = patient['date_of_birth']
                diagnosis_default = patient.get('diagnosis', '')
                break
            else:
                # New patient
                print("New patient - please enter details")
                last_name = input("Last name: ").strip()
                first_name = input("First name: ").strip()
                dob = input("Date of birth (YYYY-MM-DD): ").strip()
                diagnosis_default = input("Diagnosis: ").strip()

                new_patient = pd.DataFrame([{
                    'PHN': phn,
                    'last_name': last_name,
                    'first_name': first_name,
                    'date_of_birth': dob,
                    'diagnosis': diagnosis_default
                }])
                patient_df = pd.concat([patient_df, new_patient], ignore_index=True)
                break

        phn_list.append(phn)
        last_name_list.append(last_name)
        first_name_list.append(first_name)
        dob_list.append(dob)

        billing_options = {
        '1': ('98010', 'LFP Direct Patient Care'),
        '2': ('98011', 'LFP Indirect Patient Care'),
        '3': ('98012', 'LFP Admin Care'),
        '4': ('98119', 'Travel Time'),
        '5': ('98031', 'LFP Office'),
        '6': ('98990', 'Primary Care Panel'),
        '0': ('98032', 'LFP Virtual (default)')
        }

        print("\nSelect billing item:")
        for key, (code, description) in billing_options.items():
            print(f"{key}: {code} - {description}")

        while True:
            billing_choice = input("Enter the number for billing item (default is 0): ").strip() or '0'
            if billing_choice in billing_options:
                billing_item, billing_description = billing_options[billing_choice]
                break
            else:
                print("Invalid choice. Please select a valid number.")

        billing_item_list.append(billing_item)

        # Auto-set diagnosis for specific billing codes
        if billing_item in ['98010', '98011', '98012', '98119', '98990']:
            billing_types = {
                '98010': 'LFP Direct Patient Care',
                '98011': 'LFP Indirect Patient Care',
                '98012': 'LFP Admin Care',
                '98119': 'Travel Time',
                '98990': 'Primary Care Panel Report'
            }
            diagnosis = 'L23'
            print(f"Diagnosis automatically set to {diagnosis} for billing code: {billing_item} - {billing_types[billing_item]}")
        else:
            # Suggest the existing/default diagnosis (editable)
            diagnosis = input(f"Diagnosis [{diagnosis_default}]: ").strip()
            if not diagnosis:
                diagnosis = diagnosis_default
        diagnosis_list.append(diagnosis)

        # Update diagnosis in patient_df for this PHN
        patient_df.loc[patient_df['PHN'] == phn, 'diagnosis'] = diagnosis

        # Time entries
        if billing_item in ['98010', '98011', '98012', '98119']:
            start_time_list.append(input("Start time (HH:MM): "))
            end_time_list.append(input("End time (HH:MM): "))
        else:
            start_time_list.append('')
            end_time_list.append('')

    # Save updated patient list
    patient_df.to_csv(patient_list_path, index=False)
    print(f"\nPatient list updated at {patient_list_path}")

    # Create service records
    service_data = {
        'date_of_service': [date_of_service] * num_rows,
        'last_name': last_name_list,
        'first_name': first_name_list,
        'PHN': phn_list,
        'date_of_birth': dob_list,
        'billing_item': billing_item_list,
        'diagnosis': diagnosis_list,
        'location': [location] * num_rows,
        'facility_code': [facility_code] * num_rows,
        'start_time': start_time_list,
        'end_time': end_time_list,
        'rural_premium': [rural_premium] * num_rows
    }

    service_df = pd.DataFrame(service_data)
    print("\nGenerated Service Records:")
    print(service_df)

    # Save service records
    save_csv = input("\nWould you like to save the service records to CSV? (y/n): ").lower()
    if save_csv == 'y':
        filename = input("Enter filename (without extension): ") + ".csv"
        service_df.to_csv(filename, index=False)
        print(f"Service records saved to {filename}")

if __name__ == "__main__":
    main()
