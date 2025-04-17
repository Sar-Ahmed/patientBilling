import pandas as pd
import os

def main():
    # Load or create patient list
    patient_list_path = 'Patient_list.csv'
    if os.path.exists(patient_list_path):
        patient_df = pd.read_csv(patient_list_path)
    else:
        patient_df = pd.DataFrame(columns=['PHN', 'last_name', 'first_name', 'date_of_birth'])
    
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
    
    # Facility code validation (must be OD411 or OD096)
    while True:
        facility_code = input("Facility code (OD411 or OD096): ").upper()
        if facility_code in ['OD411', 'OD096']:
            break
        print("Invalid facility code. Must be OD411 or OD096.")
    
    location = input("Location (default is 'L'): ") or "L"
    
    # Rural Premium - simplified to just 'B'
    rural_premium = 'Big White' if input("Rural Premium (enter 'B' for Big White or leave empty): ").upper() == 'B' else None
    
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
            
            # Check if patient exists
            patient_match = patient_df[patient_df['PHN'] == phn]
            if not patient_match.empty:
                # Existing patient - auto-fill details
                patient = patient_match.iloc[0]
                print(f"Found existing patient: {patient['first_name']} {patient['last_name']}")
                last_name = patient['last_name']
                first_name = patient['first_name']
                dob = patient['date_of_birth']
                break
            else:
                # New patient - collect details
                print("New patient - please enter details")
                last_name = input("Last name: ").strip()
                first_name = input("First name: ").strip()
                dob = input("Date of birth (YYYY-MM-DD): ").strip()
                
                # Add to patient list
                new_patient = pd.DataFrame([{
                    'PHN': phn,
                    'last_name': last_name,
                    'first_name': first_name,
                    'date_of_birth': dob
                }])
                patient_df = pd.concat([patient_df, new_patient], ignore_index=True)
                break
        
        # Store for current session
        phn_list.append(phn)
        last_name_list.append(last_name)
        first_name_list.append(first_name)
        dob_list.append(dob)
        
        # Get billing item with default
        billing_item = input("Billing item (default is 98032): ") or "98032"
        billing_item_list.append(billing_item)
        
        # Set diagnosis to L23 if billing item is 98010 or 98011
        if billing_item in ['98010', '98011']:
            diagnosis = 'L23'
            print(f"Diagnosis automatically set to {diagnosis} for this billing code")
        else:
            diagnosis = input("Diagnosis: ")
        diagnosis_list.append(diagnosis)
        
        # Time entries for specific billing codes
        if billing_item in ['98010', '98011']:
            start_time_list.append(input("Start time (HH:MM): "))
            end_time_list.append(input("End time (HH:MM): "))
        else:
            start_time_list.append('')
            end_time_list.append('')
    
    # Save updated patient list
    patient_df.to_csv(patient_list_path, index=False)
    print(f"\nPatient list updated at {patient_list_path}")
    
    # Create service records dataframe
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