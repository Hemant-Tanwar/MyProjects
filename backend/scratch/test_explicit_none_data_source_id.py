from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pool = [p for p in c.data_integration.get_data_pools() if p.name == pool_name][0]
    master_pool = [p for p in c.data_integration.get_data_pools() if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    sql = f'DROP VIEW IF EXISTS AFKO; CREATE VIEW AFKO AS SELECT * FROM "{master_pool.id}"."AFKO";'
    
    job_name = "Test Job Explicit None"
    for j in pool.get_jobs():
        if j.name == job_name:
            j.delete()
            break
            
    print("Creating job with data_source_id=None explicitly...")
    job = pool.create_job(name=job_name, data_source_id=None)
    t = job.create_transformation(name="SQL Transformation", statement=sql)
    
    print("Executing job...")
    try:
        job.execute(wait=True)
        print("Success!")
    except Exception as e:
        print("Failed:", e)
        print(job._get_execution_detailed_error_log())
    finally:
        job.delete()

except Exception as e:
    print("Error:", e)
