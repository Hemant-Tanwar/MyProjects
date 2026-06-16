from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    p = c.data_integration.get_data_pools()[0]
    
    payload = {
        "name": "Probe Connection",
        "type": "FILES"
    }
    
    endpoints = [
        f"/integration/api/pools/{p.id}/data-sources",
        f"/integration/api/pools/{p.id}/data-sources/",
        f"/integration/api/pools/{p.id}/connections",
        f"/integration/api/pools/{p.id}/connections/",
        f"/integration/api/pools/{p.id}/datasources",
        f"/integration/api/pools/{p.id}/datasources/",
        f"/integration/api/pools/{p.id}/data-connections",
        f"/integration/api/pools/{p.id}/data-connections/",
        "/integration/api/data-sources",
        "/integration/api/data-sources/",
        "/integration/api/datasource",
        "/integration/api/datasource/",
        "/integration/api/connections",
        "/integration/api/connections/",
    ]
    
    for ep in endpoints:
        print(f"\n--- POST {ep} ---")
        try:
            resp = c.client.request("POST", ep, json=payload)
            print("Success! Status code:", resp.status_code if hasattr(resp, 'status_code') else "N/A")
            print("Response:", resp.json() if hasattr(resp, 'json') else resp)
        except Exception as e:
            # Print exception message
            err_msg = str(e)
            if "status" in err_msg or "allowed" in err_msg.lower() or "not found" in err_msg.lower():
                print("Failed:", err_msg[:300])
            else:
                print("Failed:", err_msg)
                
except Exception as e:
    print("Error:", e)
