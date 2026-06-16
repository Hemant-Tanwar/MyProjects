from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pools = c.data_integration.get_data_pools()
    pool = [p for p in pools if p.name == pool_name][0]
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    # Get all master tables
    master_tables = [t.name.upper() for t in master_pool.get_tables() if not t.name.upper().startswith("CELONIS_")]
    print(f"Found {len(master_tables)} master tables to link.")
    
    job = pool.create_job(name="All Views Link Job Command Line")
    
    view_statements = []
    for table in master_tables:
        view_statements.append(f"DROP VIEW IF EXISTS {table};")
        view_statements.append(f"CREATE VIEW {table} AS SELECT * FROM \"{master_pool.id}\".\"{table}\";")
        
    sql = "\n".join(view_statements)
    
    t = job.create_transformation(name="T_ALL_VIEWS", statement=sql)
    print(f"Executing job to link all 51+ tables on pool {pool.name}...")
    try:
        job.execute(wait=True)
        print("Succeeded! All tables linked successfully via views.")
    except Exception as e:
        print("Failed:", e)
        
    t.delete()
    job.delete()
        
except Exception as e:
    print("Error:", e)
