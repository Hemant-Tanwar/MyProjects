from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

def probe():
    celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
    p = celonis.data_integration.get_data_pools()[0]
    
    candidates = [
        ("POST", f"integration/api/pools/{p.id}/data-sources"),
        ("POST", f"integration/api/pools/{p.id}/data-sources/"),
        ("POST", f"integration/api/pools/{p.id}/connections"),
        ("POST", f"integration/api/pools/{p.id}/connections/"),
        ("POST", "integration/api/pools/data-sources"),
        ("POST", "integration/api/pools/data-sources/"),
        ("POST", "integration/api/data-sources"),
        ("POST", "integration/api/data-sources/"),
        ("POST", "integration/api/datasource"),
        ("POST", "integration/api/datasource/"),
    ]
    
    payload = {
        "name": "Data_source",
        "type": "FILES",
        "poolId": p.id
    }
    
    for method, path in candidates:
        try:
            print(f"Trying {method} {path}...")
            resp = celonis.client.request(method, path, json=payload)
            print(f"-> SUCCESS: {resp}")
        except Exception as e:
            print(f"-> FAILED: {str(e)[:200]}")

if __name__ == "__main__":
    probe()
