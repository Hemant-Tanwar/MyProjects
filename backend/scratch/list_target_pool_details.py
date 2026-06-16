from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pool = [p for p in c.data_integration.get_data_pools() if p.name == pool_name][0]
    
    print("=== TABLES AND VIEWS IN TARGET POOL ===")
    tables = pool.get_tables()
    print(f"Total tables/views found: {len(tables)}")
    for t in sorted(tables, key=lambda x: x.name):
        print(f" - {t.name} (Type: {type(t).__name__})")
        
    print("\n=== JOBS ===")
    jobs = pool.get_jobs()
    for j in jobs:
        print(f" - Job: {j.name}")
        for t in j.get_transformations():
            print(f"   * Transformation: {t.name}")
            
except Exception as e:
    print("Error:", e)
