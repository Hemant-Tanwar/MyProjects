from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    for space in c.studio.get_spaces():
        print(f"Space: {space.name}")
        for pkg in space.get_packages():
            print(f"  Package: {pkg.name} (key: {pkg.key})")
            print(f"    Views: {[v.name for v in pkg.get_views()]}")
            print(f"    Analyses: {[a.name for a in pkg.get_analyses()]}")
            print(f"    KMs: {[km.key for km in pkg.get_knowledge_models()]}")
except Exception as e:
    print("Error:", e)
