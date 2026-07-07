from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool = c.data_integration.get_data_pools()[0]
    dm = pool.get_data_models()[0] if pool.get_data_models() else None
    if dm:
        print("DataModel class:", type(dm))
        print("create_process_configuration signature:")
        print(inspect.signature(dm.create_process_configuration))
        print("\ncreate_foreign_key signature:")
        print(inspect.signature(dm.create_foreign_key))
except Exception as e:
    print("Error:", e)
