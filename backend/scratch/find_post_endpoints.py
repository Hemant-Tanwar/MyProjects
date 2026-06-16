from pycelonis.service.integration.service import IntegrationService

methods = [x for x in dir(IntegrationService) if x.startswith("post_")]
for m in sorted(methods):
    print(m)
