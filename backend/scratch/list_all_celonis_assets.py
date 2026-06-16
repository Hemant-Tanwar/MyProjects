from pycelonis import get_celonis
import json

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
spaces = c.studio.get_spaces()

print(f"Total spaces found: {len(spaces)}")
for space in spaces:
    print(f"\n==================================================")
    print(f"Space: {space.name} (ID: {space.id})")
    print(f"==================================================")
    try:
        packages = space.get_packages()
        print(f"Packages count: {len(packages)}")
        for pkg in packages:
            print(f"  Package: {pkg.name} (Key: {pkg.key})")
            
            # Check views
            views = pkg.get_views()
            print(f"    Views count: {len(views)}")
            for v in views:
                print(f"      - View: {v.name} (Key: {v.key})")
                
            # Check analyses
            analyses = pkg.get_analyses()
            print(f"    Analyses count: {len(analyses)}")
            for a in analyses:
                print(f"      - Analysis: {a.name} (Key: {a.key})")
                # print a snippet of the serialized_content to see its keys
                if a.serialized_content:
                    try:
                        content_dict = json.loads(a.serialized_content)
                        print(f"        Serialized keys: {list(content_dict.keys())}")
                        if "draft" in content_dict and content_dict["draft"]:
                            print(f"        Draft keys: {list(content_dict['draft'].keys())}")
                    except:
                        pass
    except Exception as e:
        print(f"  Error reading space {space.name}: {e}")
