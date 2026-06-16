from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")

print("Checking Studio Space and Package...")
space = [s for s in celonis.studio.get_spaces() if "Procure to Pay P2P" in s.name][0]
package = space.get_packages()[0]
print(f"Space: {space.name}, Package: {package.name} (Key: {package.key})")

print("\n--- Package Variables ---")
for v in package.get_variables():
    print(f"  Variable Key: {v.key}, Type: {v.type_}, Value: {v.value}")

print("\n--- Knowledge Models ---")
for km in package.get_knowledge_models():
    print(f"  KM Key: {km.key}")
    try:
        content = km.get_content()
        print(f"    kind: {content.kind}")
        print(f"    data_model_id: {content.data_model_id}")
        print(f"    kpis count: {len(content.kpis)}")
        print(f"    filters count: {len(content.filters)}")
    except Exception as e:
        print(f"    Failed to fetch content: {e}")

print("\n--- Views ---")
for view in package.get_views():
    print(f"  View Name: {view.name}, Key: {view.key}")
    content = view.serialized_content
    if content:
        try:
            parsed = json.loads(content)
            print("    Successfully parsed serialized_content JSON!")
            print("    Metadata:")
            print(json.dumps(parsed.get("metadata", {}), indent=4))
            print(f"    Layout Rows: {len(parsed.get('layout', {}).get('rows', []))}")
            print(f"    Components count: {len(parsed.get('components', []))}")
            for c in parsed.get('components', []):
                print(f"      - ID: {c.get('id')}, Type: {c.get('type')}, Settings: {c.get('settings')}")
        except Exception as e:
            print(f"    Failed to parse JSON content: {e}")
            print("    Content raw prefix:", content[:300])
