from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
spaces = celonis.studio.get_spaces()
found = False
for space in spaces:
    for package in space.get_packages():
        for view in package.get_views():
            content = view.serialized_content
            if content and len(content) > 200:
                print(f"Space: {space.name}, Package: {package.name}, View: {view.name}")
                print(f"Length: {len(content)}")
                try:
                    parsed = json.loads(content)
                    print(json.dumps(parsed, indent=2)[:2000])
                except Exception as e:
                    print("Failed to parse JSON:", e)
                    print(content[:2000])
                print("-" * 50)
                found = True

if not found:
    print("No views with serialized content > 200 bytes found.")
