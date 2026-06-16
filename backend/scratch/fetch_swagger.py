from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    
    endpoints = [
        "integration/v2/api-docs",
        "integration/api/v2/api-docs",
        "integration/swagger-resources",
        "integration/swagger-ui.html",
    ]
    
    for ep in endpoints:
        print(f"\n--- GET {ep} ---")
        try:
            resp = c.client.request("GET", ep)
            print("Success! Length:", len(resp.text))
            # Print first 200 chars
            print(resp.text[:200])
        except Exception as e:
            print("Failed:", str(e)[:200])
            
except Exception as e:
    print("Error:", e)
