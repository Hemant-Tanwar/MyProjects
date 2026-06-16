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
    
    # Test Method A: Set statement in create_transformation
    print("\n--- Testing Method A (statement in create_transformation) ---")
    job_a = pool.create_job(name="Test Job Method A")
    try:
        t_a = job_a.create_transformation(name="T_A", statement=sql)
        job_a.execute(wait=True)
        print("Method A: Success!")
    except Exception as e:
        print("Method A: Failed:", e)
    finally:
        job_a.delete()
        
    # Test Method B: Set statement using update_statement
    print("\n--- Testing Method B (using update_statement) ---")
    job_b = pool.create_job(name="Test Job Method B")
    try:
        t_b = job_b.create_transformation(name="T_B")
        t_b.update_statement(sql)
        job_b.execute(wait=True)
        print("Method B: Success!")
    except Exception as e:
        print("Method B: Failed:", e)
    finally:
        job_b.delete()

except Exception as e:
    print("Error:", e)
