from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    
    for p in pools:
        if p.name in ["Accounts Payable Direct Push", "Accounts Payable Direct Push Test Pool"]:
            print(f"\n=== Pool: {p.name} (ID: {p.id}) ===")
            print("Permissions:", p.permissions if hasattr(p, "permissions") else "N/A")
            print("Connections:")
            for conn in p.get_data_connections():
                print(f" - {conn.name} (ID: {conn.id})")
            print("Tables count:", len(p.get_tables()))
            print("Jobs count:", len(p.get_jobs()))
            
except Exception as e:
    print("Error:", e)
