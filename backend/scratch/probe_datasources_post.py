from pycelonis import get_celonis
import json

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
pools = c.data_integration.get_data_pools()
master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
target_pool = [p for p in pools if p.name == "Accounts Payable Direct Push"][0]

master_id = master_pool.id
target_id = target_pool.id

print(f"Master Pool ID: {master_id}")
print(f"Target Pool ID: {target_id}")

# Inspect what data-sources/ returns for both pools
for pool_id, label in [(master_id, "MASTER"), (target_id, "TARGET")]:
    path = f"integration/api/pools/{pool_id}/data-sources/"
    print(f"\n=== GET {label} {path} ===")
    try:
        resp = c.client.request("GET", path)
        # Try to get raw response object
        print("Status:", resp.status_code if hasattr(resp, 'status_code') else type(resp))
        try:
            data = resp.json()
            print("Response JSON:", json.dumps(data, indent=2)[:2000])
        except:
            print("Response text:", str(resp)[:500])
    except Exception as e:
        print("Error:", e)

# Now try POST with various payloads to the target pool's data-sources/
print("\n\n=== Trying POST payloads to target pool data-sources/ ===")
payloads = [
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL", "dataPoolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL", "pool_id": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL", "poolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "connectionType": "DATA_POOL", "dataPoolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "datasourceType": "DATA_POOL", "dataPoolId": master_id},
]

for i, payload in enumerate(payloads):
    path = f"integration/api/pools/{target_id}/data-sources/"
    print(f"\n--- Payload {i+1}: {payload} ---")
    try:
        resp = c.client.request("POST", path, json=payload)
        print("Status:", resp.status_code if hasattr(resp, 'status_code') else type(resp))
        try:
            data = resp.json()
            print("Response:", json.dumps(data, indent=2)[:1000])
        except:
            print("Response:", str(resp)[:500])
    except Exception as e:
        err = str(e)
        print("Error:", err[:600])
