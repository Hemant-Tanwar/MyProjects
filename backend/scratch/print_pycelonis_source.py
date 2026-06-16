from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool = c.data_integration.get_data_pools()[0]
    
    from pycelonis.service.integration.service import IntegrationService
    print("IntegrationService methods:")
    methods = [x for x in dir(IntegrationService) if not x.startswith("_")]
    for m in sorted(methods):
        print(f"  {m}")
            
except Exception as e:
    import traceback
    traceback.print_exc()


