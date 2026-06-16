from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pool = [p for p in c.data_integration.get_data_pools() if p.name == pool_name][0]
    master_pool = [p for p in c.data_integration.get_data_pools() if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    master_tables = [t.name.upper() for t in master_pool.get_tables()]
    
    view_statements = []
    for table_name in master_tables:
        t_upper = table_name.upper()
        if t_upper.startswith("CELONIS_") or t_upper == "DUMMY" or t_upper == "DUMMY_CONNECTION_INIT":
            continue
        view_statements.append(f"DROP VIEW IF EXISTS {t_upper};")
        view_statements.append(f"CREATE VIEW {t_upper} AS SELECT * FROM \"{master_pool.id}\".\"{t_upper}\";")
        
    sql = "\n".join(view_statements)
    
    job_name = "Accounts Payable Direct Push Data Job" # Using the exact name from main.py
    
    # Delete if exists
    for j in pool.get_jobs():
        if j.name == job_name:
            print("Deleting existing job...")
            j.delete()
            break
            
    print(f"Creating job '{job_name}'...")
    job = pool.create_job(name=job_name)
    t = job.create_transformation(name="SQL Transformation", statement=sql)
    
    print("Executing job...")
    try:
        job.execute(wait=True)
        print("Success!")
    except Exception as e:
        print("Failed:", e)
        print("Detailed Error Log:")
        print(job._get_execution_detailed_error_log())
    finally:
        job.delete()

except Exception as e:
    print("Error:", e)
