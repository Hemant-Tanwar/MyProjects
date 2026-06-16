from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push Test Pool"
    pools = c.data_integration.get_data_pools()
    pool = [p for p in pools if p.name == pool_name][0]
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    job = pool.create_job(name="Multi Semicolon Test Job")
    
    # Test: Multiple CREATE VIEW statements separated by semicolon (unquoted view names)
    sql = (
        f'DROP VIEW IF EXISTS EKKO;\n'
        f'CREATE VIEW EKKO AS SELECT * FROM "{master_pool.id}"."EKKO";\n'
        f'DROP VIEW IF EXISTS LFA1;\n'
        f'CREATE VIEW LFA1 AS SELECT * FROM "{master_pool.id}"."LFA1";'
    )
    t = job.create_transformation(name="T_MULTI", statement=sql)
    print("Testing multiple view creations with semicolons...")
    try:
        job.execute(wait=True)
        print("Succeeded!")
    except Exception as e:
        print("Failed:", e)
        
    t.delete()
    job.delete()
        
except Exception as e:
    print("Error:", e)
