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

# Candidate endpoints for creating a data pool connection share
candidates = [
    ("GET",  f"integration/api/pools/{master_id}/data-sources"),
    ("GET",  f"integration/api/pools/{master_id}/data-sources/"),
    ("POST", f"integration/api/pools/{target_id}/data-sources", {
        "name": "SAP_Dictionary_Master_Pool",
        "type": "DATA_POOL",
        "dataPoolId": master_id
    }),
    ("POST", f"integration/api/pools/{target_id}/data-sources/", {
        "name": "SAP_Dictionary_Master_Pool",
        "type": "DATA_POOL",
        "dataPoolId": master_id
    }),
    ("POST", f"integration/api/pools/{master_id}/data-sources", {
        "name": "SAP_Dictionary_Master_Pool Share",
        "type": "DATA_POOL",
        "targetPoolId": target_id
    }),
    ("POST", f"integration/api/pools/{target_id}/connections", {
        "name": "SAP_Dictionary_Master_Pool",
        "type": "DATA_POOL",
        "poolId": master_id
    }),
    ("POST", f"integration/api/pools/{target_id}/connections/", {
        "name": "SAP_Dictionary_Master_Pool",
        "type": "DATA_POOL",
        "poolId": master_id
    }),
    ("POST", f"integration/api/data-pool-shares", {
        "sourcePoolId": master_id,
        "targetPoolId": target_id
    }),
    ("POST", f"integration/api/data-pool-shares/", {
        "sourcePoolId": master_id,
        "targetPoolId": target_id
    }),
    ("POST", f"integration/api/pools/{master_id}/shares", {
        "targetPoolId": target_id
    }),
    ("POST", f"integration/api/pools/{master_id}/shares/", {
        "targetPoolId": target_id
    }),
    ("POST", f"integration/api/pools/share", {
        "sourcePoolId": master_id,
        "targetPoolId": target_id
    }),
    ("GET",  f"integration/api/pools/{target_id}/data-sources"),
    ("GET",  f"integration/api/pools/{target_id}/data-sources/"),
]

for item in candidates:
    method = item[0]
    path   = item[1]
    body   = item[2] if len(item) > 2 else None
    print(f"\n--- {method} {path} ---")
    try:
        if method == "GET":
            resp = c.client.request("GET", path)
        else:
            resp = c.client.request("POST", path, json=body)
        print(f"SUCCESS ({resp.status_code if hasattr(resp, 'status_code') else '?'}):", json.dumps(resp if isinstance(resp, dict) else str(resp))[:400])
    except Exception as e:
        print("FAILED:", str(e)[:300])
