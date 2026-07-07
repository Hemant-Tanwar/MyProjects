import os
import pandas as pd
from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool = [p for p in c.data_integration.get_data_pools() if p.name == "O2C"][0]
    
    csv_path = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source/VBAK.CSV"
    df = pd.read_csv(csv_path)
    print("VBAK shape:", df.shape)
    
    # Try creating the table in O2C pool
    print("Uploading VBAK...")
    pool.create_table(df=df, table_name="VBAK", drop_if_exists=True)
    print("Upload successful!")
except Exception as e:
    print("Error:", e)
