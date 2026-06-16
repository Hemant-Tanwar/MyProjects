from pycelonis.service.integration.service import IntegrationService

print("=== IntegrationService methods with 'data_source' ===")
for x in dir(IntegrationService):
    if "data_source" in x or "datasource" in x:
        print(f" - {x}")
        
print("\n=== IntegrationService methods with 'connection' ===")
for x in dir(IntegrationService):
    if "connection" in x:
        print(f" - {x}")
