from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    print("Available Data Pools:")
    for p in pools:
        tables = p.get_tables()
        print(f"- Pool Name: {p.name} (ID: {p.id}), Tables Count: {len(tables)}")
        if "Master" in p.name or len(tables) < 10:
            print("  Tables list:")
            for t in tables[:10]:
                print(f"    * {t.name}")
            if len(tables) > 10:
                print(f"    ... and {len(tables) - 10} more")
except Exception as e:
    print("Error:", e)
