from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    for pool in pools:
        print(f"\nPool: {pool.name}")
        conns = pool.get_data_connections()
        print(f"Data connections ({len(conns)}):")
        for conn in conns:
            print(f" - Connection Name: {conn.name}, ID: {conn.id}")
            # Let's inspect methods of connection
            print(f"   Connection properties: {conn.json_dict() if hasattr(conn, 'json_dict') else conn.dict()}")
except Exception as e:
    print("Error:", e)
