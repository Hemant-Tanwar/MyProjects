from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    print("All Data Pools on Celonis:")
    for p in pools:
        # Check attributes of pool
        print(f" - Name: {p.name}")
        print(f"   ID: {p.id}")
        # Let's check if we can get transport/dict representation
        if hasattr(p, 'json_dict'):
            print(f"   Details: {p.json_dict()}")
        elif hasattr(p, 'dict'):
            print(f"   Details: {p.dict()}")
except Exception as e:
    print("Error:", e)
