import pycelonis
import sys

# Print module attributes
print("=== pycelonis attributes ===")
print([x for x in dir(pycelonis) if not x.startswith("_")])

# Let's inspect where get_celonis comes from
from pycelonis import get_celonis
print("get_celonis module:", get_celonis.__module__)

# Let's import the connection class from where it lives
c = get_celonis(
    base_url="https://wbd8lqn9-2026-06-12.training.celonis.cloud/", 
    api_token="Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs",
    key_type="USER_KEY"
)
pool = c.data_integration.get_data_pools()[0]
# We don't have a connection, but we can look at the type of the return value annotation
import inspect
sig = inspect.signature(pool.get_data_connection)
print("get_data_connection return type:", sig.return_annotation)
if sig.return_annotation != inspect.Signature.empty:
    conn_cls = sig.return_annotation
    print("Class methods:")
    print([x for x in dir(conn_cls) if not x.startswith("_")])
else:
    # Let's look at DataPool methods
    print("get_data_connection signature:", sig)
