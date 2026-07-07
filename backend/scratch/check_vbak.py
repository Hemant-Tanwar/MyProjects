from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    for pool in pools:
        print(f"Data Pool: {pool.name}")
        tables = pool.get_tables()
        for t in tables:
            print(f"  Table: {t.name}, Type: {t.type_ if hasattr(t, 'type_') else '?'}")
except Exception as e:
    print("Error:", e)
