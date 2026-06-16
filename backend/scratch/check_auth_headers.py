import httpx
import json
from pycelonis import get_celonis

base_url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

# First find what auth headers pycelonis uses
c = get_celonis(base_url=base_url + "/", api_token=api_token, key_type="USER_KEY")

# Check what headers the pycelonis client sends by inspecting a known-good request
resp = c.client.request("GET", f"integration/api/pools/3f91bc4b-ce28-4302-b238-2e8c233eaa8e/data-sources/")
print("GET status:", resp.status_code if hasattr(resp, 'status_code') else "Response object")
print("Response headers (if any):", getattr(resp, 'headers', {}))

# Try to get cookies/auth from the client
client_obj = c.client
print("\nClient type:", type(client_obj))
print("Client attrs:", [x for x in dir(client_obj) if not x.startswith("_")])

# Get the underlying httpx client if available
underlying = getattr(client_obj, 'client', None) or getattr(client_obj, '_client', None) or getattr(client_obj, 'session', None)
if underlying:
    print("\nUnderlying client type:", type(underlying))
    print("Headers:", dict(underlying.headers) if hasattr(underlying, 'headers') else "N/A")
    print("Cookies:", dict(underlying.cookies) if hasattr(underlying, 'cookies') else "N/A")
