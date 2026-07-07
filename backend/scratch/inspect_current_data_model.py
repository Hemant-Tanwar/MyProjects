from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool = [p for p in c.data_integration.get_data_pools() if p.name == "O2C"][0]
    dm = [m for m in pool.get_data_models() if m.name == "O2C Data Model"][0]
    
    print("Tables in Data Model:")
    for t in dm.get_tables():
        print(f"  - {t.name} (id: {t.id})")
        
    print("\nForeign Keys in Data Model:")
    for fk in dm.get_foreign_keys():
        print(f"  - Source Table ID: {fk.source_table_id}")
        print(f"    Target Table ID: {fk.target_table_id}")
        print(f"    Columns: {fk.columns}")
        
    print("\nProcess Configurations:")
    for pc in dm.get_process_configurations():
        print(f"  - Activity Table ID: {pc.activity_table_id}")
        print(f"    Case ID Column: {pc.case_id_column}")
        print(f"    Activity Column: {pc.activity_column}")
        print(f"    Timestamp Column: {pc.timestamp_column}")
        print(f"    Sorting Column: {pc.sorting_column}")
        print(f"    Case Table ID: {pc.case_table_id}")
except Exception as e:
    print("Error:", e)
