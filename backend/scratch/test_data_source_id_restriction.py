from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pool = [p for p in c.data_integration.get_data_pools() if p.name == pool_name][0]
    master_pool = [p for p in c.data_integration.get_data_pools() if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    # Get the dummy connection ID from the table
    tbl = pool.get_table("dummy_connection_init")
    data_source_id = tbl.data_source_id
    print(f"Dummy Table: {tbl.name}, Connection ID: {data_source_id}")
    
    sql = f'DROP VIEW IF EXISTS AFKO; CREATE VIEW AFKO AS SELECT * FROM "{master_pool.id}"."AFKO";'
    
    # Test 1: With data_source_id
    print("\n--- Test 1: Creating job WITH data_source_id ---")
    job_with = pool.create_job(name="Test Job With Connection ID", data_source_id=data_source_id)
    t_with = job_with.create_transformation(name="T_WITH", statement=sql)
    try:
        job_with.execute(wait=True)
        print("Test 1: Success!")
    except Exception as e:
        print("Test 1: Failed:", e)
        print(job_with._get_execution_detailed_error_log())
    finally:
        job_with.delete()
        
    # Test 2: Without data_source_id
    print("\n--- Test 2: Creating job WITHOUT data_source_id ---")
    job_without = pool.create_job(name="Test Job Without Connection ID")
    t_without = job_without.create_transformation(name="T_WITHOUT", statement=sql)
    try:
        job_without.execute(wait=True)
        print("Test 2: Success!")
    except Exception as e:
        print("Test 2: Failed:", e)
        print(job_without._get_execution_detailed_error_log())
    finally:
        job_without.delete()

except Exception as e:
    print("Error:", e)
