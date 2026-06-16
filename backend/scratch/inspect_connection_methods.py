from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    conn = None
    for pool in pools:
        conns = pool.get_data_connections()
        if conns:
            conn = conns[0]
            print(f"Found connection in pool {pool.name}")
            break
            
    if conn:
        print("DataConnection methods:")
        for x in dir(conn):
            if not x.startswith("_"):
                print(f"  {x}")
    else:
        print("No connections found in any pool.")
except Exception as e:
    print("Error:", e)
