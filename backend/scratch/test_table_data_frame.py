from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pools = c.data_integration.get_data_pools()
    print("Found pools:", [p.name for p in pools])
    for pool in pools:
        tables = pool.get_tables()
        if tables:
            t = tables[0]
            print(f"Testing table: {t.name} from pool: {pool.name}")
            if hasattr(t, "get_data_frame"):
                try:
                    df = t.get_data_frame()
                    print("Successfully called get_data_frame. Shape:", df.shape)
                    print(df.head())
                except Exception as ex:
                    print("Error calling get_data_frame:", ex)
            else:
                print("Table does not have get_data_frame method.")
            break
except Exception as e:
    print("Error:", e)
