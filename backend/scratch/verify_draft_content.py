from pycelonis import get_celonis
from pycelonis.service.package_manager.service import PackageManagerService

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Procurement" in s.name][0]
package = [p for p in space.get_packages() if p.key == "procurement-process-optimization-2363b3c3"][0]
view = package.get_views()[0]

print("Package:", package.name, "Key:", package.key)
print("View:", view.name, "Key:", view.key, "ID:", view.id)
print("View fields:")
print(f" - working_draft_id: {view.working_draft_id}")
print(f" - draft_id: {view.draft_id}")
print(f" - activated_draft_id: {view.activated_draft_id}")

print("\n1. Fetching Node with no draft_id:")
node_no_draft = PackageManagerService.get_api_nodes_id(view.client, view.id)
print(f" - Content length: {len(node_no_draft.serialized_content) if node_no_draft.serialized_content else 0}")
if node_no_draft.serialized_content:
    print(f" - Content snippet: {node_no_draft.serialized_content[:300]}")

print("\n2. Fetching Node with draft_id=view.working_draft_id:")
node_with_draft = PackageManagerService.get_api_nodes_id(view.client, view.id, draft_id=view.working_draft_id)
print(f" - Content length: {len(node_with_draft.serialized_content) if node_with_draft.serialized_content else 0}")
if node_with_draft.serialized_content:
    print(f" - Content snippet: {node_with_draft.serialized_content[:300]}")
