from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Procurement" in s.name][0]
package = [p for p in space.get_packages() if p.key == "procurement-process-optimization-2363b3c3"][0]

print("Creating a temporary view...")
temp_view = package.create_view(name="TEMP_TEST_EMPTY_VIEW_999")
try:
    print(f"View ID: {temp_view.id}")
    print(f"Working Draft ID: {temp_view.working_draft_id}")
    print(f"Draft ID: {temp_view.draft_id}")
    print(f"Serialization Type: {temp_view.serialization_type}")
    print(f"Serialized Content: {repr(temp_view.serialized_content)}")
finally:
    print("Deleting temporary view...")
    temp_view.delete()
