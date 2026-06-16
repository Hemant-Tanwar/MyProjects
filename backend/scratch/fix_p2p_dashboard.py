from pycelonis import get_celonis
from pycelonis.service.blueprint.service import Blueprint, BoardAssetType, BoardUpsertRequest
import yaml

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Procurement" in s.name][0]
package = [p for p in space.get_packages() if p.key == "procurement-process-optimization-2363b3c3"][0]
view = package.get_views()[0]
kms = package.get_knowledge_models()
km_key = kms[0].key if kms else None

print(f"Updating View: {view.name} (Key: {view.key}) with flat settings...")

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
            },
            {
                "id": "row-2",
                "order": 200,
                "columns": [
                    {
                        "id": "col-2-1",
                        "size": 12,
                        "order": 100,
                        "componentId": "PROCESS_EXPLORER_P2P"
                    }
                ]
            },
            {
                "id": "row-3",
                "order": 300,
                "columns": [
                    {
                        "id": "col-3-1",
                        "size": 3,
                        "order": 100,
                        "componentId": "FILTER_MAVERICK"
                    },
                    {
                        "id": "col-3-2",
                        "size": 9,
                        "order": 200,
                        "componentId": "CHART_VENDOR_EFFICIENCY"
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
                "kpi": "THROUGHPUT_TIME_PO_TO_GR"
            }
        },
        {
            "id": "KPI_AUTOMATION",
            "type": "kpi-card",
            "settings": {
                "title": "Touchless PO Rate",
                "kpi": "AUTOMATION_RATE"
            }
        },
        {
            "id": "KPI_PO_VALUE",
            "type": "kpi-card",
            "settings": {
                "title": "Total PO Spend Volume",
                "kpi": "TOTAL_PO_VALUE"
            }
        },
        {
            "id": "PROCESS_EXPLORER_P2P",
            "type": "process-explorer",
            "settings": {
                "title": "P2P Process Variant flow",
                "eventLogs": [
                    {
                        "eventLog": "TEMP_P2P_EVENT_LOG"
                    }
                ]
            }
        },
        {
            "id": "FILTER_MAVERICK",
            "type": "dropdown",
            "settings": {
                "title": "Show Maverick Buying",
                "filter": "MAVERICK_BUYING_FILTER"
            }
        },
        {
            "id": "CHART_VENDOR_EFFICIENCY",
            "type": "column-chart",
            "settings": {
                "title": "PO Count by Supplier Country",
                "dimension": "VENDOR_COUNTRY",
                "kpi": "TOTAL_PO_VALUE"
            }
        }
    ]
}

yaml_content = yaml.dump(view_config, sort_keys=False)
print("Uploading View via put_api_boards_board_id using YAML and BOARD_V2...")
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

print("Publishing package to 1.0.5...")
try:
    package.publish(version="1.0.5")
    print("Version 1.0.5 published successfully!")
except Exception as e:
    print("Package publish failed:", e)

view.sync()
print("\nRefetched view serialization type:", view.serialization_type)
print("Refetched view serialized_content:")
print(view.serialized_content)
