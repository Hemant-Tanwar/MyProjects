from pycelonis import get_celonis
import time

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pool = [p for p in c.data_integration.get_data_pools() if p.name == pool_name][0]
    
    print(f"Target Pool: {pool.name}")
    conns = pool.get_data_connections()
    print(f"Found {len(conns)} connections in target pool.")
    
    # We look for a shared data pool connection
    shared_conn = None
    for conn in conns:
        print(f"Connection: {conn.name} (ID: {conn.id}, Type: {conn.type_ if hasattr(conn, 'type_') else 'N/A'})")
        # Shared pool connections are of type "DATA_POOL" or have "pool" in their name/type
        if conn.type_ == "DATA_POOL" or "pool" in str(conn.name).lower() or "share" in str(conn.name).lower():
            shared_conn = conn
            break
            
    if shared_conn:
        print(f"\nUsing shared connection: {shared_conn.name}")
        # List tables in the connection
        tables = shared_conn.get_tables()
        print(f"Available tables in shared connection: {len(tables)}")
        for t in tables[:10]:
            print(f" - {t.name}")
        if len(tables) > 10:
            print(f" ... and {len(tables) - 10} more")
            
        # Synchronize tables (replicate them)
        reps = shared_conn.get_replications()
        print(f"\nExisting replications in pool: {len(reps)}")
        
        # Let's create replications for all 51 tables if they don't exist
        for t in tables:
            tname = t.name.upper()
            # Check if replication already exists for this table
            existing_rep = None
            for rep in reps:
                if rep.table_name.upper() == tname:
                    existing_rep = rep
                    break
            if not existing_rep:
                print(f"Creating replication for {tname}...")
                try:
                    rep = shared_conn.create_replication(table_name=t.name)
                    print(f"Created replication for {tname} (ID: {rep.id})")
                except Exception as cre_err:
                    print(f"Failed to create replication for {tname}: {cre_err}")
            else:
                print(f"Replication for {tname} already exists (ID: {existing_rep.id})")
                
        # Re-fetch replications
        reps = shared_conn.get_replications()
        
        # Trigger initialization of all replications
        print("\nTriggering initialization for all replications...")
        for rep in reps:
            print(f"Initializing replication {rep.table_name}...")
            try:
                rep.initialize()
            except Exception as init_err:
                print(f"Failed to initialize {rep.table_name}: {init_err}")
                
        # Poll statuses
        print("\nPolling replication statuses...")
        while True:
            all_done = True
            for rep in reps:
                rep.sync()
                print(f" - Table {rep.table_name}: Status = {rep.status if hasattr(rep, 'status') else 'N/A'}")
                if rep.status not in ["SUCCESS", "FAILED"]:
                    all_done = False
            if all_done:
                print("All replications completed!")
                break
            time.sleep(5)
            
    else:
        print("\nNo shared data pool connection found in target pool.")
        print("Please share the master pool connection in Celonis UI first.")
        
except Exception as e:
    print("Error:", e)
