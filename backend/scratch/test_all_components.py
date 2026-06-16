from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
space = celonis.studio.get_spaces()[0]
package = space.get_packages()[0]
view = package.get_views()[0]
kms = package.get_knowledge_models()
km_key = kms[0].key if kms else None

# Let's test all components
components = [
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
            "eventLogs": [{"eventLog": "TEMP_P2P_EVENT_LOG"}]
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

layout = {
    "rows": [
        {
            "id": "row-1",
            "order": 100,
            "columns": [
                {"id": "col-1-1", "size": 4, "order": 100, "componentId": "KPI_THROUGHPUT"},
                {"id": "col-1-2", "size": 4, "order": 200, "componentId": "KPI_AUTOMATION"},
                {"id": "col-1-3", "size": 4, "order": 300, "componentId": "KPI_PO_VALUE"}
            ]
        },
        {
            "id": "row-2",
            "order": 200,
            "columns": [
                {"id": "col-2-1", "size": 12, "order": 100, "componentId": "PROCESS_EXPLORER_P2P"}
            ]
        },
        {
            "id": "row-3",
            "order": 300,
            "columns": [
                {"id": "col-3-1", "size": 3, "order": 100, "componentId": "FILTER_MAVERICK"},
                {"id": "col-3-2", "size": 9, "order": 200, "componentId": "CHART_VENDOR_EFFICIENCY"}
            ]
        }
    ]
}

config = {
    "metadata": {
        "key": view.key,
        "name": view.name,
        "template": False,
        "knowledgeModelKey": km_key
    },
    "layout": layout,
    "components": components
}

view.serialized_content = json.dumps(config)
try:
    view.update()
    print("Successfully updated!")
    refetched = package.get_views()[0]
    # Let's format and print the entire refetched JSON
    parsed = json.loads(refetched.serialized_content)
    print("Refetched layout and components:")
    print(json.dumps(parsed, indent=2))
except Exception as e:
    print("Failed:", e)
