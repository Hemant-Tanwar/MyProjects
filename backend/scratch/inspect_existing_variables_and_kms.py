from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
spaces = celonis.studio.get_spaces()
for space in spaces:
    print(f"Space: {space.name}")
    for p in space.get_packages():
        print(f"  Package: {p.name}")
        vars_list = p.get_variables()
        if vars_list:
            print("    Variables:")
            for v in vars_list:
                print(f"      key={v.key}, type={v.type_}, value={v.value}")
        kms = p.get_knowledge_models()
        if kms:
            print("    Knowledge Models:")
            for km in kms:
                print(f"      key={km.key}")
                print(f"      content={km.content}")
