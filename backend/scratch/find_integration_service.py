from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool = c.data_integration.get_data_pools()[0]
    
    # We inspect globals of get_data_connections
    func = pool.get_data_connections
    gls = func.__globals__
    
    # Print keys that contain 'Service' or 'Integration'
    print("Globals matching:")
    for k in gls.keys():
        if "Service" in k or "Integration" in k or "DataSource" in k:
            print(f"  {k} -> {gls[k]}")
            
except Exception as e:
    print("Error:", e)
