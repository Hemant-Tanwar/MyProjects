import pycelonis
import pprint

# Let's find classes in pycelonis related to connection
for attr in dir(pycelonis):
    if "conn" in attr.lower():
        print(f"pycelonis.{attr}")

from pycelonis.celonis_api.data_integration.data_connection import DataConnection
print("\n=== DataConnection class attributes ===")
pprint.pprint([x for x in dir(DataConnection) if not x.startswith("_")])
