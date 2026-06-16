from pycelonis.service.integration.service import IntegrationService
import inspect

print("=== IntegrationService POST/PUT/DELETE Methods ===")
methods = [x for x in dir(IntegrationService) if x.startswith("post_") or x.startswith("put_") or x.startswith("delete_") or "conn" in x]
for m in sorted(methods):
    print(m)
