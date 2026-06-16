from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    p = c.data_integration.get_data_pools()[0]
    
    endpoints = [
        f"integration/api/pools/{p.id}/connections",
        f"integration/api/pools/{p.id}/data-sources",
        "integration/api/connection-types",
        "integration/api/connections/types",
        "integration/api/data-sources/types",
    ]
    
    for ep in endpoints:
        print(f"\n--- GET {ep} ---")
        try:
            resp = c.client.request("GET", ep)
            print("Success! Response:")
            import pprint
            if isinstance(resp, list):
                pprint.pprint(resp[:10])
            else:
                pprint.pprint(resp)
        except Exception as e:
            print("Failed:", str(e)[:200])
            
except Exception as e:
    print("Error:", e)
