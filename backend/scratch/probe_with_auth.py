import json
from pycelonis import get_celonis

base_url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=base_url, api_token=api_token, key_type="USER_KEY")
pools = c.data_integration.get_data_pools()
master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
target_pool = [p for p in pools if p.name == "Accounts Payable Direct Push"][0]

master_id = master_pool.id
target_id = target_pool.id

# Use pycelonis client (which handles auth correctly) but get the raw response
# We use the underlying httpx client but with c.client.client (which already has cookies)
underlying = c.client.client  # httpx.Client

# The pycelonis client headers + cookies
headers = dict(underlying.headers)
headers.update(c.client.headers)
headers["Content-Type"] = "application/json"

print("Headers used:", {k: v for k, v in headers.items() if k.lower() != "authorization"})
print("Cookies:", dict(underlying.cookies))

payloads = [
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL", "dataPoolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL", "poolId": master_id},
    {"dataPoolId": master_id},
    {"type": "DATA_POOL", "poolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL"},
]

endpoint = f"{base_url.rstrip('/')}/integration/api/pools/{target_id}/data-sources/"

for i, payload in enumerate(payloads):
    print(f"\n--- Payload {i+1}: {payload} ---")
    try:
        resp = underlying.post(endpoint, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        try:
            print("Body:", json.dumps(resp.json(), indent=2)[:800])
        except:
            print("Body:", resp.text[:400])
    except Exception as e:
        print("Exception:", str(e)[:300])
