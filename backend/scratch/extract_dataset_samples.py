import os
import pandas as pd

kaggle_path = "/Users/hemanttanwar/.cache/kagglehub/datasets/mustafakeser4/sap-dataset-bigquery-dataset/versions/1"
data_source_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source"

os.makedirs(data_source_dir, exist_ok=True)

files = [f for f in os.listdir(kaggle_path) if f.endswith(".csv")]
print(f"Found {len(files)} CSV files in Kaggle dataset.")

for idx, f in enumerate(files):
    src_path = os.path.join(kaggle_path, f)
    dest_name = f.upper()
    dest_path = os.path.join(data_source_dir, dest_name)
    
    print(f"[{idx+1}/{len(files)}] Processing {f} -> {dest_name}...")
    try:
        # Read first 200 rows to ensure we capture realistic relational data
        df = pd.read_csv(src_path, nrows=200)
        # Write to destination
        df.to_csv(dest_path, index=False)
        print(f"  Saved {len(df)} rows. Columns: {len(df.columns)}")
    except Exception as e:
        print(f"  Error processing {f}: {e}")

print("\nExtraction completed! All tables created in Data_source.")
