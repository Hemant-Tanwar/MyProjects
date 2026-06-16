from pycelonis import get_celonis
import pandas as pd
import time

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pools = c.data_integration.get_data_pools()
    pool = [p for p in pools if p.name == pool_name][0]
    
    df = pd.DataFrame({"col": [1]})
    tbl = pool.create_table(df=df, table_name="DUMMY_TEST_ID", drop_if_exists=True)
    
    print("Sleeping 3 seconds for Celonis to sync...")
    time.sleep(3)
    
    print("Listing connections after sleep:")
    conns = pool.get_data_connections()
    for conn in conns:
        print(f" - {conn.name} (ID: {conn.id})")
        
except Exception as e:
    print("Error:", e)
