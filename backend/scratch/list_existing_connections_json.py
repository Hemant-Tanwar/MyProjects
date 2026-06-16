from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    for p in pools:
        print(f"\nPool: {p.name} ({p.id})")
        try:
            # Let's call the integration service directly
            from pycelonis.service.integration.service import IntegrationService
            res = IntegrationService.get_api_pools_pool_id_data_sources(c.client, pool_id=p.id)
            print(f"Data Sources count: {len(res)}")
            for ds in res:
                print("Data Source Detail:")
                print(ds.json_dict() if hasattr(ds, 'json_dict') else ds)
        except Exception as e:
            print("Failed to get data sources:", e)
            
except Exception as e:
    print("Error:", e)
