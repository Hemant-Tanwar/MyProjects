from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push Test Pool"
    pools = c.data_integration.get_data_pools()
    pool = [p for p in pools if p.name == pool_name][0]
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    job = pool.create_job(name="No Temp Prefix Test Job")
    
    # Test: CREATE VIEW EKKO without TEMP_ prefix
    sql = f'CREATE VIEW EKKO AS SELECT * FROM "{master_pool.id}"."EKKO"'
    t = job.create_transformation(name="T_EKKO", statement=sql)
    print("Testing CREATE VIEW EKKO (No TEMP_ prefix) on fresh job...")
    try:
        job.execute(wait=True)
        print("Succeeded!")
    except Exception as e:
        print("Failed:", e)
        
    t.delete()
    job.delete()
        
except Exception as e:
    print("Error:", e)
