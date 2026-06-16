from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    master_pool = [p for p in c.data_integration.get_data_pools() if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    tables = master_pool.get_tables()
    print(f"Total tables in master pool: {len(tables)}")
    
    for t in sorted(tables, key=lambda x: x.name):
        # Print first few tables to verify columns exist
        if t.name.upper() in ["MARA", "EKKO", "EKPO", "LFA1"]:
            print(f"\n- Table: {t.name}")
            try:
                print(f"  Columns ({len(t.columns)}): {[col.name for col in t.columns[:10]]}...")
            except Exception as e:
                print(f"  Could not read columns: {e}")
                
except Exception as e:
    print("Error:", e)
