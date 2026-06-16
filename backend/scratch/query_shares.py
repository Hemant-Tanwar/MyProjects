from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    p = c.data_integration.get_data_pools()[0]
    
    endpoints = [
        "integration/api/shares",
        "integration/api/shares/",
        f"integration/api/pools/{p.id}/shares",
        f"integration/api/pools/{p.id}/shares/",
        f"integration/api/pools/{p.id}/shared-pools",
        f"integration/api/pools/{p.id}/shared-pools/",
        f"integration/api/pools/{p.id}/shared-connections",
        f"integration/api/pools/{p.id}/shared-connections/",
    ]
    
    for ep in endpoints:
        print(f"\n--- GET {ep} ---")
        try:
            resp = c.client.request("GET", ep)
            print("Success! Response:")
            import pprint
            pprint.pprint(resp.json() if hasattr(resp, 'json') else resp)
        except Exception as e:
            print("Failed:", str(e)[:200])
            
except Exception as e:
    print("Error:", e)
