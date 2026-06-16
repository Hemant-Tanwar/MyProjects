import httpx
import json

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

master_id = "3f91bc4b-ce28-4302-b238-2e8c233eaa8e"
target_id = "c30bdfdb-f639-4607-a96f-200b2b1adddd"

headers = {
    "Authorization": f"AppKey {api_token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

client = httpx.Client(headers=headers, follow_redirects=True)

# Try various payloads
payloads = [
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL", "dataPoolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "type": "DATA_POOL", "poolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "datasourceType": "DATA_POOL", "poolId": master_id},
    {"name": "SAP_Dictionary_Master_Pool", "connectionType": "DATA_POOL", "poolId": master_id},
]

endpoints = [
    f"{url}/integration/api/pools/{target_id}/data-sources/",
    f"{url}/integration/api/pools/{target_id}/data-sources",
]

for endpoint in endpoints:
    for i, payload in enumerate(payloads):
        print(f"\n--- POST {endpoint} payload={i+1} ---")
        try:
            resp = client.post(endpoint, json=payload)
            print(f"Status: {resp.status_code}")
            try:
                print("Body:", json.dumps(resp.json(), indent=2)[:1000])
            except:
                print("Body:", resp.text[:500])
        except Exception as e:
            print("Exception:", str(e)[:300])

client.close()
