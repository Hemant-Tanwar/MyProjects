from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
print("=== All Spaces on Celonis ===")
for s in c.studio.get_spaces():
    print(f"- Name: {s.name}, ID: {s.id}")
    for p in s.get_packages():
        print(f"   Package: {p.name}, Key: {p.key}, ID: {p.id}")
