from pycelonis import get_celonis
import json

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
pool = [p for p in c.data_integration.get_data_pools() if p.name == "Accounts Payable Direct Push"][0]

print(f"Pool: {pool.name} (ID: {pool.id})")

# List all tables in the pool to see if TEMP tables exist
print("\n=== Tables in Pool ===")
tables = pool.get_tables()
for t in sorted(tables, key=lambda x: x.name):
    print(f"  {t.name}")

# List all jobs
print("\n=== Jobs in Pool ===")
jobs = pool.get_jobs()
for j in jobs:
    print(f"\n  Job: {j.name} (ID: {j.id})")
    # Get transformations
    transforms = j.get_transformations()
    for t in transforms:
        print(f"    Transformation: {t.name}")
    
    # Get execution history
    try:
        status = j.get_current_execution_status()
        print(f"    Last Status: {getattr(status, 'status', status)}")
    except Exception as e:
        print(f"    Could not get status: {e}")
    
    # Try to get error log
    try:
        error_log = j._get_execution_detailed_error_log()
        if error_log:
            print(f"    Error Log:\n{error_log[:1000]}")
    except Exception as e:
        print(f"    Could not get error log: {e}")
