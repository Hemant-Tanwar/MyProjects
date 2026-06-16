from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
dm_id = "9481a30a-3fd1-4b93-8b32-a24e9c10bc61"

print("Fetching Data Model...")
try:
    # Let's find the data model in the pool
    # We can get pools and find the data model by ID
    pools = c.data_integration.get_data_pools()
    found_dm = None
    for pool in pools:
        for dm in pool.get_data_models():
            if dm.id == dm_id:
                found_dm = dm
                print(f"Found DM in Pool: {pool.name}")
                break
        if found_dm:
            break
            
    if found_dm:
        print("Data Model Name:", found_dm.name)
        print("Tables in Data Model:")
        tables = found_dm.get_tables()
        for t in tables:
            print(f"- {t.name} (id: {t.id})")
    else:
        print("Data Model with ID not found in any pools!")
except Exception as e:
    print("Verification failed:", e)
