from pycelonis import get_celonis
import pandas as pd

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push Test Pool"
    
    # 1. Get or create pool
    pools = c.data_integration.get_data_pools()
    pool = None
    for p in pools:
        if p.name == pool_name:
            pool = p
            break
    if pool:
        print("Deleting existing test pool...")
        pool.delete()
        
    print("Creating new test pool...")
    pool = c.data_integration.create_data_pool(name=pool_name)
    
    # 2. Upload dummy table to force creation of data connection
    print("Uploading dummy table to force connection creation...")
    df_dummy = pd.DataFrame({"col": [1]})
    pool.create_table(df=df_dummy, table_name="DUMMY", drop_if_exists=True)
    
    conns = pool.get_data_connections()
    print("Data connections after upload:")
    for conn in conns:
        print(f" - {conn.name} (ID: {conn.id})")
        
    # 3. Create job
    print("Creating data job...")
    job = pool.create_job(name="Test SQL Job")
    
    # 4. Create cross-pool view statement
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    sql = f'DROP VIEW IF EXISTS "EKKO"; CREATE VIEW "EKKO" AS SELECT * FROM "{master_pool.id}"."EKKO";'
    
    print("Creating transformation...")
    trans = job.create_transformation(name="SQL Transformation")
    trans.update_statement(sql)
    
    print("Executing job...")
    job.execute(wait=True)
    status = job.get_current_execution_status()
    print("Job status:", status.status if hasattr(status, 'status') else str(status))
    
except Exception as e:
    import traceback
    traceback.print_exc()
