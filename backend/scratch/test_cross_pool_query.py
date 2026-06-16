from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    print("Pools:")
    for p in pools:
        print(f"  Name: {p.name}, ID: {p.id}")
        
    # Let's take the first pool as Pool A and second as Pool B
    pool_a = pools[0]
    pool_b = None
    for p in pools:
        if p.id != pool_a.id and p.get_tables():
            pool_b = p
            break
            
    if not pool_b:
        print("Could not find a second pool with tables.")
    else:
        print(f"Testing query from Pool A ({pool_a.name}) to Pool B ({pool_b.name}, ID: {pool_b.id})")
        table_b_name = pool_b.get_tables()[0].name
        print(f"Querying table {table_b_name} from Pool B schema...")
        
        job = pool_a.create_job(name="Cross Pool Test Job")
        sql = f"CREATE VIEW TEMP_CROSS_TEST AS SELECT * FROM \"{pool_b.id}\".\"{table_b_name}\" LIMIT 5;"
        
        # Clean existing test transformation
        for t in job.get_transformations():
            t.delete()
            
        t = job.create_transformation(name="Test SQL", statement=sql)
        print("Executing job...")
        try:
            job.execute(wait=True)
            print("Job executed successfully! Cross-pool query works!")
        except Exception as exec_err:
            print("Execution failed:", exec_err)
        finally:
            job.delete()
except Exception as e:
    print("Error:", e)
