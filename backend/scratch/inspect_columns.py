from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    for pool in pools:
        tables = pool.get_tables()
        if tables:
            t = tables[0]
            print(f"Table: {t.name}")
            cols = t.get_columns()
            print("Columns count:", len(cols))
            if cols:
                col = cols[0]
                print("Column class:", type(col))
                for attr in dir(col):
                    if not attr.startswith("_"):
                        print(f"  {attr}: {getattr(col, attr)}")
            break
except Exception as e:
    print("Error:", e)
