import pandas as pd
import os
import glob
import io

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

# Let's examine the infections file more closely (with repair)
try:
    repaired_csv = repair_multiline_csv('diagnosis codes/Diagnosis_Code_INFECTIONS.csv')
    # Force Code column to be treated as string to prevent numeric conversion
    df = pd.read_csv(repaired_csv, dtype={'Code': str})
    print(f"Infections file (repaired) has {len(df)} rows")
    print(f"Columns: {df.columns.tolist()}")
    
    # Look for problematic rows
    print("\nChecking for rows with empty codes:")
    empty_codes = df[df['Code'].isna() | (df['Code'] == '')]
    print(f"Rows with empty codes: {len(empty_codes)}")
    if not empty_codes.empty:
        print("Empty code rows:")
        for idx, row in empty_codes.iterrows():
            print(f"Row {idx}: Code='{row['Code']}', Description='{row['Description']}'")
    
    # Look for the specific problematic area around line 380
    print("\nChecking rows around line 380:")
    for i in range(375, 385):
        if i < len(df):
            row = df.iloc[i]
            print(f"Row {i}: Code='{row['Code']}', Description='{row['Description']}'")
    
    # Look for code 075 specifically
    print("\nLooking for code 075:")
    code_075_rows = df[df['Code'] == '075']
    print(f"Rows with code 075: {len(code_075_rows)}")
    if not code_075_rows.empty:
        for idx, row in code_075_rows.iterrows():
            print(f"Row {idx}: Code='{row['Code']}', Description='{row['Description']}'")
    
    # Check if there are any codes that start with 075
    print("\nChecking for codes starting with 075:")
    codes_starting_with_075 = df[df['Code'].astype(str).str.startswith('075')]
    print(f"Codes starting with 075: {len(codes_starting_with_075)}")
    if not codes_starting_with_075.empty:
        for idx, row in codes_starting_with_075.iterrows():
            print(f"Row {idx}: Code='{row['Code']}', Description='{row['Description']}'")
    
    # Check for any NaN values in the data
    print("\nChecking for NaN values:")
    nan_counts = df.isna().sum()
    print(nan_counts)
    
except Exception as e:
    print(f"Error reading infections file: {e}")

print("\n" + "="*50)
print("Testing the load_diagnosis_codes function:")

def load_diagnosis_codes():
    """Load all diagnosis codes from CSV files in the diagnosis codes folder, repairing multi-line descriptions if needed."""
    all_codes = []
    diagnosis_folder = 'diagnosis codes'
    
    if os.path.exists(diagnosis_folder):
        # Get all CSV files in the diagnosis codes folder
        csv_files = glob.glob(os.path.join(diagnosis_folder, '*.csv'))
        
        for csv_file in csv_files:
            try:
                repaired_csv = repair_multiline_csv(csv_file)
                # Force Code column to be treated as string to prevent numeric conversion
                df = pd.read_csv(repaired_csv, dtype={'Code': str})
                print(f"Loading {csv_file}: {len(df)} rows")
                
                # Check if the file has Code and Description columns
                if 'Code' in df.columns and 'Description' in df.columns:
                    # Clean the data - remove rows with NaN values
                    df_cleaned = df.dropna(subset=['Code', 'Description'])
                    print(f"After dropping NaN: {len(df_cleaned)} rows")
                    
                    # Convert Code to string and handle any remaining NaN values
                    df_cleaned['Code'] = df_cleaned['Code'].astype(str).fillna('')
                    df_cleaned['Description'] = df_cleaned['Description'].fillna('')
                    
                    # Additional cleaning - remove any rows with empty codes or descriptions
                    df_cleaned = df_cleaned[
                        (df_cleaned['Code'].str.strip() != '') & 
                        (df_cleaned['Description'].str.strip() != '')
                    ]
                    print(f"After removing empty codes/descriptions: {len(df_cleaned)} rows")
                    
                    # Add filename as category for organization
                    category = os.path.basename(csv_file).replace('.csv', '').replace('Diagnosis_Code_', '')
                    df_cleaned['Category'] = category
                    all_codes.append(df_cleaned)
                    
                    # Check for 075 in this file
                    code_075_in_file = df_cleaned[df_cleaned['Code'] == '075']
                    if not code_075_in_file.empty:
                        print(f"Found 075 in {csv_file}: {code_075_in_file.iloc[0].to_dict()}")
                    
            except Exception as e:
                print(f"Could not load {csv_file}: {str(e)}")
    
    if all_codes:
        # Combine all dataframes
        combined_df = pd.concat(all_codes, ignore_index=True)
        print(f"Combined dataframe: {len(combined_df)} rows")
        
        # Create a searchable format: "Code - Description (Category)"
        combined_df['Searchable'] = combined_df['Code'].astype(str) + ' - ' + combined_df['Description'] + ' (' + combined_df['Category'] + ')'
        
        # Convert to list and ensure all values are strings
        searchable_list = combined_df['Searchable'].astype(str).tolist()
        
        return searchable_list
    else:
        return []

# Test the function
codes = load_diagnosis_codes()

# Look for code 075
found_075 = False
for code in codes:
    if code.startswith('075 -'):
        print(f"Found 075 in final list: {code}")
        found_075 = True
        break

if not found_075:
    print("Code 075 not found in the final loaded codes")

print(f"Total codes loaded: {len(codes)}")

# Look for code 075
found_075 = False
for code in codes:
    if code.startswith('075 -'):
        print(f"Found 075: {code}")
        found_075 = True
        break

if not found_075:
    print("Code 075 not found in the loaded codes")
    
    # Let's check the infections file specifically
    try:
        df = pd.read_csv('diagnosis codes/Diagnosis_Code_INFECTIONS.csv')
        print(f"Infections file has {len(df)} rows")
        
        # Look for 075 in the raw data
        code_075_row = df[df['Code'] == '075']
        if not code_075_row.empty:
            print(f"Found 075 in raw data: {code_075_row.iloc[0].to_dict()}")
        else:
            print("075 not found in raw infections file")
            
        # Check for any codes starting with 075
        codes_starting_with_075 = df[df['Code'].astype(str).str.startswith('075')]
        print(f"Codes starting with 075: {len(codes_starting_with_075)}")
        if not codes_starting_with_075.empty:
            print(codes_starting_with_075)
            
    except Exception as e:
        print(f"Error reading infections file: {e}")

print(f"Total codes loaded: {len(codes)}")
print("First 10 codes:")
for i, code in enumerate(codes[:10]):
    print(f"{i+1}: {code}") 