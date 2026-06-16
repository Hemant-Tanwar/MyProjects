from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Procurement" in s.name][0]
package = [p for p in space.get_packages() if p.key == "procurement-process-optimization-2363b3c3"][0]

print("Package:", package.name, "Key:", package.key)
print("Variables in package:")
for v in package.get_variables():
    print(v.json_dict())
