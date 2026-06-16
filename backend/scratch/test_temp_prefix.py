from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push Test Pool"
    pools = c.data_integration.get_data_pools()
    pool = [p for p in pools if p.name == pool_name][0]
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    job = pool.get_jobs()[0]
    trans = job.get_transformations()[0]
    
    # Test 1: CREATE VIEW TEMP_EKKO
    sql1 = f'CREATE VIEW TEMP_EKKO AS SELECT * FROM "{master_pool.id}"."EKKO"'
    print("Testing Test 1 (CREATE VIEW TEMP_EKKO)...")
    trans.update_statement(sql1)
    try:
        job.execute(wait=True)
        print("Test 1 Succeeded!")
    except Exception as e:
        print("Test 1 Failed:", e)

    # Test 2: CREATE VIEW EKKO (without TEMP_ prefix)
    sql2 = f'CREATE VIEW EKKO AS SELECT * FROM "{master_pool.id}"."EKKO"'
    print("\nTesting Test 2 (CREATE VIEW EKKO)...")
    trans.update_statement(sql2)
    try:
        job.execute(wait=True)
        print("Test 2 Succeeded!")
    except Exception as e:
        print("Test 2 Failed:", e)
        
except Exception as e:
    print("Error:", e)
