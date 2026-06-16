from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    print("Master Pool Name:", master_pool.name)
    print("Master Pool Data Connections:")
    for conn in master_pool.get_data_connections():
        print(f" - Connection Name: {conn.name}, ID: {conn.id}, Type: {conn.type if hasattr(conn, 'type') else 'N/A'}")
except Exception as e:
    print("Error:", e)
