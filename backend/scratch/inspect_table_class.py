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
            print("Table Class:", type(t))
            for attr in sorted(dir(t)):
                if not attr.startswith("_"):
                    try:
                        val = getattr(t, attr)
                        print(f"  {attr}: {type(val)}")
                    except Exception as ex:
                        print(f"  {attr}: Error: {ex}")
            break
except Exception as e:
    print("Error:", e)
