from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    for space in c.studio.get_spaces():
        for pkg in space.get_packages():
            views = pkg.get_views()
            for v in views:
                print(f"View Name: {v.name}, Key: {v.key}")
                print("Serialized Content:")
                print(v.serialized_content[:3000])
                print("="*80)
except Exception as e:
    print("Error:", e)
