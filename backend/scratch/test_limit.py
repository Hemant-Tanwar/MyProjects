from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push Test Pool"
    pools = c.data_integration.get_data_pools()
    pool = [p for p in pools if p.name == pool_name][0]
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    job = pool.create_job(name="Limit Test Job")
    
    # Test 1: No limit, no semicolon
    sql1 = f'CREATE VIEW TEMP_EKKO_1 AS SELECT * FROM "{master_pool.id}"."EKKO"'
    t1 = job.create_transformation(name="T1", statement=sql1)
    print("Testing Test 1 (No limit, no semicolon)...")
    try:
        job.execute(wait=True)
        print("Test 1 Succeeded!")
    except Exception as e:
        print("Test 1 Failed:", e)
    t1.delete()

    # Test 2: No limit, with semicolon
    sql2 = f'CREATE VIEW TEMP_EKKO_2 AS SELECT * FROM "{master_pool.id}"."EKKO";'
    t2 = job.create_transformation(name="T2", statement=sql2)
    print("\nTesting Test 2 (No limit, with semicolon)...")
    try:
        job.execute(wait=True)
        print("Test 2 Succeeded!")
    except Exception as e:
        print("Test 2 Failed:", e)
    t2.delete()

    # Test 3: With limit 5, with semicolon
    sql3 = f'CREATE VIEW TEMP_EKKO_3 AS SELECT * FROM "{master_pool.id}"."EKKO" LIMIT 5;'
    t3 = job.create_transformation(name="T3", statement=sql3)
    print("\nTesting Test 3 (With limit 5, with semicolon)...")
    try:
        job.execute(wait=True)
        print("Test 3 Succeeded!")
    except Exception as e:
        print("Test 3 Failed:", e)
    t3.delete()
    
    job.delete()
        
except Exception as e:
    print("Error:", e)
