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
    
    # Test 1: CREATE OR REPLACE VIEW without semicolon
    sql1 = f'CREATE OR REPLACE VIEW EKKO AS SELECT * FROM "{master_pool.id}"."EKKO"'
    print("Testing Test 1 (CREATE OR REPLACE VIEW without semicolon)...")
    trans.update_statement(sql1)
    try:
        job.execute(wait=True)
        print("Test 1 Succeeded!")
    except Exception as e:
        print("Test 1 Failed:", e)
        
    # Test 2: Multiple statements with semicolon but no double quotes on view name
    sql2 = f'DROP VIEW IF EXISTS EKKO;\nCREATE OR REPLACE VIEW EKKO AS SELECT * FROM "{master_pool.id}"."EKKO";'
    print("\nTesting Test 2 (Multiple statements with semicolon, no double quotes on view name)...")
    trans.update_statement(sql2)
    try:
        job.execute(wait=True)
        print("Test 2 Succeeded!")
    except Exception as e:
        print("Test 2 Failed:", e)

    # Test 3: Multiple CREATE OR REPLACE VIEW statements separated by semicolon
    sql3 = f'CREATE OR REPLACE VIEW EKKO AS SELECT * FROM "{master_pool.id}"."EKKO";\nCREATE OR REPLACE VIEW LFA1 AS SELECT * FROM "{master_pool.id}"."LFA1";'
    print("\nTesting Test 3 (Multiple CREATE OR REPLACE VIEW statements with semicolon)...")
    trans.update_statement(sql3)
    try:
        job.execute(wait=True)
        print("Test 3 Succeeded!")
    except Exception as e:
        print("Test 3 Failed:", e)
        
except Exception as e:
    print("Error:", e)
