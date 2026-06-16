from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
spaces = celonis.studio.get_spaces()
space = spaces[0]
packages = space.get_packages()
p = packages[0]

# Retrieve the actual data model id to associate
# Let's find a data model in the pool
pools = celonis.data_integration.get_data_pools()
pool = pools[0]
dms = pool.get_data_models()
if not dms:
    print("No data models found!")
    exit(1)
dm = dms[0]
print(f"Data Model ID: {dm.id}")

# Manage the package variable 'data-model'
vars_list = p.get_variables()
for v in vars_list:
    if v.key == "data-model":
        v.delete()

print("Creating variable 'data-model' pointing to the data model...")
p.create_variable(key="data-model", value=dm.id, type_="DATA_MODEL", runtime=False)

# Delete existing test KM if exists
kms = p.get_knowledge_models()
for km in kms:
    if km.key == "test-km":
        km.delete()

# Create Knowledge Model content pointing to the package variable
km_content = {
    "kind": "BASE",
    "metadata": {
        "key": "test-km",
        "displayName": "Test KM with Variable",
    },
    "dataModelId": "${{data-model}}", # Reference the package variable key using ${{var_key}} syntax
    "kpis": [],
    "filters": []
}

print("Creating Knowledge Model...")
try:
    km = p.create_knowledge_model(content=km_content)
    print("Successfully created Knowledge Model!")
    # Let's inspect the created KM content
    print("KM content from Celonis:", km.content)
except Exception as e:
    print("Failed to create Knowledge Model:", e)
    if hasattr(e, "response"):
        print("Response status code:", e.response.status_code)
        print("Response body:", e.response.text)
    # Print the exception details
    import traceback
    traceback.print_exc()
