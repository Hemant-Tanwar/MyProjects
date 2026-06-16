from pycelonis.service.integration.service import IntegrationService
import inspect

try:
    print("=== Source of get_api_pools_pool_id_data_sources ===")
    print(inspect.getsource(IntegrationService.get_api_pools_pool_id_data_sources))
    
    print("\n=== Source of delete_api_pools_pool_id_data_sources_data_source_id ===")
    print(inspect.getsource(IntegrationService.delete_api_pools_pool_id_data_sources_data_source_id))
except Exception as e:
    print("Error:", e)
