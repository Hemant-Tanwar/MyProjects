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

print("Space:", space.name)
print("Package:", package.name, "Key:", package.key)

# 1. Update/Recreate Knowledge Model with Event Log Metadata
print("\nUpdating/Recreating Knowledge Model with Event Log metadata...")
km_key = f"{package.key}-km-2363b3c3-v2"
existing_km = None
for existing in package.get_knowledge_models():
    print(f"Existing KM key: {existing.key} (expected: {km_key})")
    if existing.key == km_key:
        existing_km = existing
        break

# Recreate variable 'data-model' only if missing
existing_var = None
for v in package.get_variables():
    if v.key == "data-model":
        existing_var = v
        break

# Find active data model ID
data_model_id = None
for dp in c.data_integration.get_data_pools():
    for dm in dp.get_data_models():
        if "Procurement" in dm.name:
            data_model_id = dm.id
            break
    if data_model_id:
        break
print("Found Data Model ID:", data_model_id)

if not existing_var:
    print("Creating variable 'data-model'...")
    package.create_variable(key="data-model", value=data_model_id, type_="DATA_MODEL", runtime=False)
else:
    print("Variable 'data-model' already exists. Current value:", existing_var.value)
    if existing_var.value != data_model_id:
        print("Updating variable value...")
        existing_var.delete()
        package.create_variable(key="data-model", value=data_model_id, type_="DATA_MODEL", runtime=False)

km_content = {
    "kind": "BASE",
    "metadata": {
        "key": km_key,
        "displayName": "Purchase-to-Pay Semantic Layer"
    },
    "dataModelId": "${{data-model}}",
    "kpis": [
        {
            "id": "THROUGHPUT_TIME_PO_TO_GR",
            "displayName": "PO Item to Goods Receipt Throughput Time",
            "description": "Calculates the average elapsed time between purchasing items and receiving them.",
            "pql": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Purchase Order Item'] TO LAST_OCCURRENCE['Receive Goods'], EVENTTIME('_cel_event_log')))"
        },
        {
            "id": "AUTOMATION_RATE",
            "displayName": "Automation Rate (Touchless PO)",
            "description": "Percentage of PO line items created and processed fully automatically without changes.",
            "pql": "COUNT(CASE WHEN PU_COUNT(TEMP_P2P_CASES, TEMP_P2P_EVENT_LOG.ACTIVITY, TEMP_P2P_EVENT_LOG.USER_NAME = 'SYSTEM') = PU_COUNT(TEMP_P2P_CASES, TEMP_P2P_EVENT_LOG.ACTIVITY) THEN TEMP_P2P_CASES.CASE_KEY END) / COUNT(TEMP_P2P_CASES.CASE_KEY) * 100.0"
        },
        {
            "id": "TOTAL_PO_VALUE",
            "displayName": "Total Purchase Order Net Value",
            "description": "Sum of PO line items values.",
            "pql": "SUM(TEMP_P2P_CASES.PO_AMOUNT)"
        }
    ],
    "filters": [
        {
            "id": "MAVERICK_BUYING_FILTER",
            "displayName": "Maverick Buying cases",
            "description": "Filter to view cases where the supplier invoice was registered prior to PO authorization.",
            "pql": "FILTER PROCESS OCCURRENCE 'Receive Invoice' BEFORE 'Create Purchase Order Item';"
        }
    ],
    "records": [
        {
            "id": "TEMP_P2P_EVENT_LOG",
            "displayName": "P2P Event Log Table",
            "pql": "\"TEMP_P2P_EVENT_LOG\""
        }
    ],
    "eventLogsMetadata": {
        "eventLogs": [
            {
                "id": "TEMP_P2P_EVENT_LOG",
                "displayName": "P2P Event Log",
                "pql": '"TEMP_P2P_EVENT_LOG"."ACTIVITY"',
                "recordId": "TEMP_P2P_EVENT_LOG"
            }
        ]
    }
}

if existing_km:
    print("Updating existing Knowledge Model...")
    existing_km.serialized_content = yaml.dump(km_content, sort_keys=False)
    existing_km.update()
    knowledge_model = existing_km
    print("KM updated successfully.")
else:
    print("Creating new Knowledge Model...")
    knowledge_model = package.create_knowledge_model(content=km_content)
    print("KM created successfully.")

# 2. Update/Recreate View with Corrected Schema
print("\nUpdating/Recreating view...")
view_key = f"{package.key}-view-2363b3c3"
view_name = "Procurement Process Optimization Dashboard"

view = None
for v in package.get_views():
    if v.key == view_key or v.name == view_name:
        view = v
        break

if not view:
    print("Creating view...")
    view = package.create_view(name=view_name, key=view_key, knowledge_model_key=knowledge_model.key)

view_config = {
    "metadata": {
        "key": view_key,
        "name": view_name,
        "template": False,
        "knowledgeModelKey": knowledge_model.key
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
            "type": "dropdown-list",
            "settings": {
                "title": "Show Maverick Buying",
                "data": {
                    "filter": "MAVERICK_BUYING_FILTER"
                }
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
print("Updating view layout with new configuration...")
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

print("Publishing package to 1.0.4...")
try:
    package.publish(version="1.0.4")
    print("Version 1.0.4 published successfully!")
except Exception as e:
    print("Package publish failed:", e)

view.sync()
print("\nRefetched view serialized_content:")
print(view.serialized_content)
