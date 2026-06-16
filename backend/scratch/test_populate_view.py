from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
space = celonis.studio.get_spaces()[0]
package = space.get_packages()[0]
views = package.get_views()
if not views:
    print("No views found!")
    exit(1)

view = views[0]
print(f"Testing on View: {view.name} (Key: {view.key})")

# Let's read the KM key to make sure it's linked
kms = package.get_knowledge_models()
km_key = kms[0].key if kms else None
print(f"Linked KM Key: {km_key}")

# Construct a test configuration dictionary with layout and components
test_config = {
    "metadata": {
        "key": view.key,
        "name": view.name,
        "template": False,
        "knowledgeModelKey": km_key
    },
    "layout": {
        "rows": [
            {
                "id": "row-1",
                "order": 100,
                "columns": [
                    {
                        "id": "col-1",
                        "size": 12,
                        "order": 100,
                        "componentId": "test-kpi-card"
                    }
                ]
            }
        ]
    },
    "components": [
        {
            "id": "test-kpi-card",
            "type": "kpi-card",
            "settings": {
                "title": "Total PO Spend Volume",
                "kpi": "TOTAL_PO_VALUE"
            }
        }
    ]
}

# Update the view's serialized_content
print("Updating view's serialized_content...")
try:
    view.serialized_content = json.dumps(test_config)
    view.update()
    print("Successfully updated View layout and pushed to Celonis!")
    
    # Refetch and check
    refetched_view = package.get_views()[0]
    print("Refetched serialized_content prefix:", refetched_view.serialized_content[:1000])
except Exception as e:
    print("Failed to update View:", e)
    import traceback
    traceback.print_exc()
