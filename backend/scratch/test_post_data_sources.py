from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    p = c.data_integration.get_data_pools()[0]
    
    # 1. Test GET with trailing slash
    print(f"GET /integration/api/pools/{p.id}/data-sources/")
    try:
        resp = c.client.request("GET", f"/integration/api/pools/{p.id}/data-sources/")
        print("Success! Data Sources:")
        print(resp)
    except Exception as e:
        print("GET Failed:", e)
        
    # 2. Test POST with trailing slash
    print(f"\nPOST /integration/api/pools/{p.id}/data-sources/")
    payload = {
        "name": "Test Data Pool Share Connection",
        "type": "DATA_POOL"
    }
    try:
        resp = c.client.request("POST", f"/integration/api/pools/{p.id}/data-sources/", json=payload)
        print("Success! Created connection:")
        print(resp)
    except Exception as e:
        print("POST Failed:", e)
        
except Exception as e:
    print("Error:", e)
