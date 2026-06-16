from pycelonis import get_celonis
from pycelonis.service.blueprint.service import Blueprint, BoardAssetType, BoardUpsertRequest
from pycelonis.service.package_manager.service import ContentNodeTransport
import yaml

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Procurement" in s.name][0]
package = [p for p in space.get_packages() if p.key == "procurement-process-optimization-2363b3c3"][0]

print("Package:", package.name, "Key:", package.key)

view_name = "Test AP KPI Dashboard"
view_key = f"{package.key}-test-ap-kpi"

# 1. Delete view if exists
for v in package.get_views():
    if v.key == view_key or v.name == view_name:
        print("Deleting existing test view...")
        v.delete()

# 2. Get KM key
kms = package.get_knowledge_models()
km_key = kms[0].key if kms else None
print("Linked KM key:", km_key)

# 3. Create view
print("Creating empty view...")
view = package.create_view(
    name=view_name,
    key=view_key,
    knowledge_model_key=km_key
)
print("View created. ID:", view.id)

# 4. Define minimal view configuration with 1 KPI Card
view_config = {
    "metadata": {
        "key": view_key,
        "name": view_name,
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
                        "id": "col-1-1",
                        "size": 4,
                        "order": 100,
                        "componentId": "KPI_PO_VALUE"
                    }
                ]
            }
        ]
    },
    "components": [
        {
            "id": "KPI_PO_VALUE",
            "type": "kpi-card",
            "settings": {
                "title": "Total PO Net Value",
                "kpi": "TOTAL_PO_VALUE"
            }
        }
    ]
}

yaml_content = yaml.dump(view_config, sort_keys=False)

print("Updating view layout configuration using BoardAssetType.BOARD_V2 (should_activate=True, should_publish=True)...")
updated_view_blueprint = Blueprint.put_api_boards_board_id(
    view.client,
    board_id=view.id,
    request_body=BoardUpsertRequest(
        id=view.id,
        configuration=yaml_content,
        parent_node_id=view.parent_node_id,
        parent_node_key=view.parent_node_key,
        root_node_key=view.root_node_key,
        board_asset_type=BoardAssetType.BOARD_V2,
    ),
    should_activate=True,
    should_publish=True,
)
print("View update response:", updated_view_blueprint.json_dict())

# 5. Let's force publish the package version
try:
    print("Publishing package to version 1.0.2...")
    package.publish(version="1.0.2")
    print("Package published successfully!")
except Exception as e:
    print("Package publish failed:", e)

# 6. Refetch and print serialized content
view.sync()
print("Refetched view serialization type:", view.serialization_type)
print("Refetched view serialized_content:")
print(view.serialized_content)
