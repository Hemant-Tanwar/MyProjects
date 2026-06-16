from pycelonis import get_celonis
import json

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
pools = c.data_integration.get_data_pools()
target_pool = [p for p in pools if p.name == "Accounts Payable Direct Push"][0]
master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]

# Query the pool's internal schema_tables to find what's actually available
print("=== Querying celonis_schema_tables ===")
try:
    resp = c.client.request("GET", f"integration/api/pools/{target_pool.id}/tables/")
    print("GET /tables/ status:", getattr(resp, 'status_code', '?'))
    try:
        print(json.dumps(resp.json(), indent=2)[:2000])
    except:
        print(resp)
except Exception as e:
    print("Error:", e)

print("\n=== Querying pool columns endpoint ===")
try:
    resp = c.client.request("GET", f"integration/api/pools/{target_pool.id}/columns/")
    print("Status:", getattr(resp, 'status_code', '?'))
    try:
        data = resp.json()
        print(json.dumps(data[:5] if isinstance(data, list) else data, indent=2)[:1000])
    except:
        print(resp)
except Exception as e:
    print("Error:", e)

# Try to access tables through integration API
print("\n=== GET integration/api/pools/{pool_id}/ ===")
try:
    resp = c.client.request("GET", f"integration/api/pools/{target_pool.id}/")
    print("Status:", getattr(resp, 'status_code', '?'))
    try:
        print(json.dumps(resp.json(), indent=2)[:1000])
    except:
        print(resp)
except Exception as e:
    print("Error:", e)

# Try to list tables via the public API
print("\n=== Using get_api_pools_id_tables ===")
try:
    from pycelonis.service.integration.service import IntegrationService
    tables = IntegrationService.get_api_pools_id_tables(c.client, target_pool.id)
    print("Tables returned:", len(tables) if hasattr(tables, '__len__') else tables)
    if tables:
        for t in tables[:10]:
            print(f"  {t}")
except Exception as e:
    print("Error:", e)
