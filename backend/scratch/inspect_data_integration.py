from pycelonis import get_celonis
import pprint

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    di = c.data_integration
    print("=== DataIntegration attributes and methods ===")
    pprint.pprint([x for x in dir(di) if not x.startswith("_")])
    
    # Let's inspect a single data pool
    pool = di.get_data_pools()[0]
    print("\n=== DataPool attributes and methods ===")
    pprint.pprint([x for x in dir(pool) if not x.startswith("_")])
    
    # Let's check connection creation methods on DataPool
    print("\n=== Methods on DataPool related to connections ===")
    for attr in dir(pool):
        if not attr.startswith("_") and ("conn" in attr.lower() or "source" in attr.lower() or "share" in attr.lower()):
            print(f"  {attr}")
            
except Exception as e:
    print("Error:", e)
