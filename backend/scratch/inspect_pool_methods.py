from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool = c.data_integration.get_data_pools()[0]
    print("DataPool methods:")
    for x in dir(pool):
        if not x.startswith("_"):
            print(f"  {x}")
            
    print("\ncreate_table signature:")
    print(inspect.signature(pool.create_table))
    
    table = pool.get_tables()[0] if pool.get_tables() else None
    if table:
        print("\nTable methods:")
        for x in dir(table):
            if not x.startswith("_"):
                print(f"  {x}")
except Exception as e:
    print("Error:", e)
