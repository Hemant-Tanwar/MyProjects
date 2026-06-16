from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pools = c.data_integration.get_data_pools()
    pool = None
    for p in pools:
        if p.name == pool_name:
            pool = p
            break
            
    if pool:
        print("Deleting pool:", pool.name)
        pool.delete()
        print("Deleted successfully!")
    else:
        print("Pool not found, nothing to delete.")
        
except Exception as e:
    print("Error:", e)
