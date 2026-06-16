import os
from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    master_pool = [p for p in c.data_integration.get_data_pools() if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    celonis_tables = {t.name.upper() for t in master_pool.get_tables()}
    print(f"Total tables in Celonis master pool: {len(celonis_tables)}")
    
    data_source_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source"
    csv_files = [f for f in os.listdir(data_source_dir) if f.lower().endswith(".csv")]
    local_tables = {os.path.splitext(f)[0].upper() for f in csv_files}
    print(f"Total CSV files in local Data_source: {len(local_tables)}")
    
    missing_in_celonis = local_tables - celonis_tables
    print(f"Local tables missing in Celonis: {missing_in_celonis}")
    
    for tbl in sorted(missing_in_celonis):
        print(f" - {tbl}")
except Exception as e:
    print("Error:", e)
