from pycelonis import get_celonis
from pycelonis.service.blueprint.service import Blueprint, BoardAssetType, BoardUpsertRequest
from pycelonis.service.package_manager.service import ContentNodeTransport
import yaml
import json

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Procurement" in s.name][0]
package = [p for p in space.get_packages() if p.key == "procurement-process-optimization-2363b3c3"][0]

print("Package:", package.name, "Key:", package.key)

view_key = f"{package.key}-view-2363b3c3"
view = package.get_views()[0]
print("Target View:", view.name, "Key:", view.key, "ID:", view.id)

# Get linked KM key
kms = package.get_knowledge_models()
km_key = kms[0].key if kms else None
print("Linked KM key:", km_key)

# Define the corrected KPI view configuration
view_config = {
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
                        "id": "col-1-1",
                        "size": 4,
                        "order": 100,
                        "componentId": "KPI_THROUGHPUT"
                    },
                    {
                        "id": "col-1-2",
                        "size": 4,
                        "order": 200,
                        "componentId": "KPI_AUTOMATION"
                    },
                    {
                        "id": "col-1-3",
                        "size": 4,
                        "order": 300,
                        "componentId": "KPI_PO_VALUE"
                    }
                ]
            }
        ]
    },
    "components": [
        {
            "id": "KPI_THROUGHPUT",
            "type": "kpi-card",
            "settings": {
                "title": "Avg Throughput Time (PO -> GR)",
                "data": {
                    "kpi": "THROUGHPUT_TIME_PO_TO_GR"
                }
            }
        },
        {
            "id": "KPI_AUTOMATION",
            "type": "kpi-card",
            "settings": {
                "title": "Touchless PO Rate",
                "data": {
                    "kpi": "AUTOMATION_RATE"
                }
            }
        },
        {
            "id": "KPI_PO_VALUE",
            "type": "kpi-card",
            "settings": {
                "title": "Total PO Spend Volume",
                "data": {
                    "kpi": "TOTAL_PO_VALUE"
                }
            }
        }
    ]
}

yaml_content = yaml.dump(view_config, sort_keys=False)

print("\nUpdating view layout configuration...")
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

print("Publishing package version to ensure changes propagate...")
try:
    package.publish(version="1.0.3")
    print("Package version 1.0.3 published successfully!")
except Exception as e:
    print("Package publish failed:", e)

view.sync()
print("\nRefetched view serialized_content:")
print(view.serialized_content)
