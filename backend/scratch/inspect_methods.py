from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    spaces = c.studio.get_spaces()
    space = [s for s in spaces if s.name == "AI Integration Test Space"][0]
    package = space.get_packages()[0]
    
    print("create_knowledge_model signature:")
    print(inspect.signature(package.create_knowledge_model))
    print("\ncreate_knowledge_model docstring:")
    print(package.create_knowledge_model.__doc__)
    
    print("\ncreate_view signature:")
    print(inspect.signature(package.create_view))
    print("\ncreate_view docstring:")
    print(package.create_view.__doc__)
    
except Exception as e:
    print("Error:", e)
