from pycelonis import get_celonis

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

def inspect():
    try:
        print("Connecting to Celonis...")
        celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
        print("Connected!")
        
        # Create a test pool
        pool_name = "Connection Inspection Test Pool"
        print(f"Creating/getting data pool: {pool_name}...")
        
        pools = celonis.data_integration.get_data_pools()
        data_pool = None
        for p in pools:
            if p.name == pool_name:
                data_pool = p
                break
        if not data_pool:
            data_pool = celonis.data_integration.create_data_pool(name=pool_name)
            
        print("\nData pool data connections:")
        connections = data_pool.get_connections()
        for conn in connections:
            print(f"Connection ID: {conn.id}, Name: {conn.name}, Type: {conn.type if hasattr(conn, 'type') else 'N/A'}")
            
        # Create a sample table
        print("\nUploading a sample table to data pool...")
        import pandas as pd
        df = pd.DataFrame({"ID": [1, 2], "VAL": ["A", "B"]})
        table = data_pool.create_table(table_name="INSPECT_TEST_TABLE", df_or_path=df, if_exists="drop")
        print("Table uploaded. Table details:")
        print(f"Table name: {table.name}, ID: {table.id if hasattr(table, 'id') else 'N/A'}")
        if hasattr(table, "connection"):
            print(f"Table connection: {table.connection}")
            if hasattr(table.connection, "name"):
                print(f"Table connection name: {table.connection.name}")
        else:
            print("Table does not have direct connection attribute. Table directories:")
            print([x for x in dir(table) if not x.startswith("_")])
            
        # Re-list connections
        print("\nRe-listing data pool data connections after upload:")
        connections = data_pool.get_connections()
        for conn in connections:
            print(f"Connection ID: {conn.id}, Name: {conn.name}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect()
