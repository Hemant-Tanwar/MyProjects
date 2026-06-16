from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    master_pool = [p for p in c.data_integration.get_data_pools() if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    print("Master Pool:", master_pool.name)
    print("Master Pool ID:", master_pool.id)
    
    tables = master_pool.get_tables()
    print(f"Total tables: {len(tables)}")
    
    connections = master_pool.get_data_connections()
    print(f"Total connections: {len(connections)}")
    for conn in connections:
        print(f" - Connection Name: {conn.name}, ID: {conn.id}, Type: {conn.type_ if hasattr(conn, 'type_') else 'N/A'}")
        
    if tables:
        print("\nFirst 5 tables details:")
        for t in list(tables)[:5]:
            print(f" - Table Name: {t.name}, DataSourceID: {t.data_source_id if hasattr(t, 'data_source_id') else 'N/A'}, Schema: {t.schema_name if hasattr(t, 'schema_name') else 'N/A'}")
            
except Exception as e:
    print("Error:", e)
