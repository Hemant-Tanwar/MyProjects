from pycelonis import get_celonis
from pycelonis.service.blueprint.service import Blueprint, BoardAssetType, BoardUpsertRequest
from pycelonis.ems.studio.content_node.view import View
import json

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Order to Cash" in s.name][0]
package = space.get_packages()[0]

print(f"Space: {space.name}, Package: {package.name} (Key: {package.key})")

view_key = f"{package.key}-json-view-test"
view_name = "JSON View Test"
km_key = [km.key for km in package.get_knowledge_models()][0]

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
                        "componentId": "KPI_THROUGHPUT"
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
                "title": "Avg Throughput Time",
                "kpi": "THROUGHPUT_TIME_SO_TO_SHIP"
            }
        }
    ]
}

# Delete existing test view if exists
for existing_view in package.get_views():
    if existing_view.key == view_key or existing_view.name == view_name:
        print(f"Deleting existing view: {existing_view.name}")
        existing_view.delete()

print("Creating new view using BoardAssetType.BOARD (JSON)...")
view_package_transport = Blueprint.post_api_boards(
    package.client,
    BoardUpsertRequest(
        configuration=json.dumps(view_config),
        board_asset_type=BoardAssetType.BOARD,
        parent_node_id=package.id,
        parent_node_key=package.key,
        root_node_key=package.key,
    ),
)

print(f"View package transport created with ID: {view_package_transport.id}")

# Fetch node
view_content_node_transport = package.get_content_node(view_package_transport.id)
view = View.from_transport(package.client, view_content_node_transport)

print(f"Created view node successfully: {view.name} (Serialization type: {view.serialization_type})")
print(f"Initial raw content length: {len(view.serialized_content) if view.serialized_content else 0}")

# Let's perform an update on it with BoardAssetType.BOARD
print("Updating view with updated configuration using put_api_boards_board_id and BoardAssetType.BOARD...")
updated_view_blueprint = Blueprint.put_api_boards_board_id(
    view.client,
    board_id=view.id,
    request_body=BoardUpsertRequest(
        id=view.id,
        configuration=json.dumps(view_config),
        parent_node_id=view.parent_node_id,
        parent_node_key=view.parent_node_key,
        root_node_key=view.root_node_key,
        board_asset_type=BoardAssetType.BOARD,
    ),
    should_activate=True,
    should_publish=True,
)
print("View updated successfully!")

# Refetch and check
refetched_views = package.get_views()
for rv in refetched_views:
    if rv.key == view_key:
        print(f"Refetched View: {rv.name}")
        print(f"  Serialization Type: {rv.serialization_type}")
        print(f"  Raw Content: {rv.serialized_content}")
