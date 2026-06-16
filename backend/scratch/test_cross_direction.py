from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    test_pool = [p for p in pools if p.name == "Accounts Payable Direct Push Test Pool"][0]
    
    # Direction A: Running job in Master Pool, querying Test Pool
    print("--- Direction A: Master Pool Job -> Querying Test Pool ---")
    job_a = master_pool.create_job(name="Dir A Test Job")
    # Query system table
    sql_a1 = f'CREATE VIEW TEMP_DIR_A_SYS AS SELECT * FROM "{test_pool.id}"."celonis_schema_columns" LIMIT 5;'
    t_a1 = job_a.create_transformation(name="Test Sys", statement=sql_a1)
    try:
        job_a.execute(wait=True)
        print("A1 (System table query) Succeeded!")
    except Exception as e:
        print("A1 Failed:", e)
        
    # Query user table (DUMMY)
    sql_a2 = f'CREATE VIEW TEMP_DIR_A_USER AS SELECT * FROM "{test_pool.id}"."DUMMY" LIMIT 5;'
    t_a2 = job_a.create_transformation(name="Test User Table", statement=sql_a2)
    try:
        job_a.execute(wait=True)
        print("A2 (User table query) Succeeded!")
    except Exception as e:
        print("A2 Failed:", e)
    job_a.delete()

    # Direction B: Running job in Test Pool, querying Master Pool
    print("\n--- Direction B: Test Pool Job -> Querying Master Pool ---")
    job_b = test_pool.create_job(name="Dir B Test Job")
    # Query system table
    sql_b1 = f'CREATE VIEW TEMP_DIR_B_SYS AS SELECT * FROM "{master_pool.id}"."celonis_schema_columns" LIMIT 5;'
    t_b1 = job_b.create_transformation(name="Test Sys", statement=sql_b1)
    try:
        job_b.execute(wait=True)
        print("B1 (System table query) Succeeded!")
    except Exception as e:
        print("B1 Failed:", e)
        
    # Query user table (EKKO)
    sql_b2 = f'CREATE VIEW TEMP_DIR_B_USER AS SELECT * FROM "{master_pool.id}"."EKKO" LIMIT 5;'
    t_b2 = job_b.create_transformation(name="Test User Table", statement=sql_b2)
    try:
        job_b.execute(wait=True)
        print("B2 (User table query) Succeeded!")
    except Exception as e:
        print("B2 Failed:", e)
    job_b.delete()
    
except Exception as e:
    print("Error:", e)
