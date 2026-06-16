from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    p = c.data_integration.get_data_pools()[0]
    
    print(f"GET /integration/api/pools/{p.id}")
    resp = c.client.request("GET", f"/integration/api/pools/{p.id}")
    import pprint
    pprint.pprint(resp.json())
    
except Exception as e:
    print("Error:", e)
