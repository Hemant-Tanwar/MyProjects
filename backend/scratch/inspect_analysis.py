from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    space = c.studio.get_spaces()[0]
    pkg = space.get_packages()[0]
    analyses = pkg.get_analyses()
    if analyses:
        an = analyses[0]
        print("Analysis class:", type(an))
        for x in dir(an):
            if not x.startswith("_"):
                print(f"  {x}")
except Exception as e:
    print("Error:", e)
