from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool = c.data_integration.get_data_pools()[0]
    
    print("get_data_connection signature:", inspect.signature(pool.get_data_connection))
    print("get_data_connection docs:", pool.get_data_connection.__doc__)
    print("get_data_connections signature:", inspect.signature(pool.get_data_connections))
    print("get_data_connections docs:", pool.get_data_connections.__doc__)
    
except Exception as e:
    print("Error:", e)
