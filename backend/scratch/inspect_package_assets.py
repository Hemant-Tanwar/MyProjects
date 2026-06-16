from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    print("Connected successfully!")
    
    # 1. Get space by iterating
    space_name = "AI Integration Test Space"
    spaces = c.studio.get_spaces()
    space = None
    for s in spaces:
        if s.name == space_name:
            space = s
            break
            
    if not space:
        print(f"Creating space: {space_name}...")
        space = c.studio.create_space(name=space_name)
    else:
        print(f"Found space: {space.name}")
    
    # 2. Create package with alphanumeric key
    pkg_name = "P2P Monitoring Optimization"
    pkg_key = "p2p-monitoring-optimization"
    
    # Check if package already exists
    packages = space.get_packages()
    package = None
    for p in packages:
        if p.key == pkg_key:
            package = p
            break
            
    if not package:
        print(f"Creating package '{pkg_name}' with key '{pkg_key}'...")
        package = space.create_package(name=pkg_name, key=pkg_key)
    else:
        print(f"Found package: {package.name} (Key: {package.key})")
        
    print("\nPackage attributes:")
    print([x for x in dir(package) if not x.startswith("_")])
    
    # Inspect methods on package for adding assets
    for attr in ["create_knowledge_model", "create_view", "create_asset", "get_knowledge_models", "get_views"]:
        print(f"Has {attr}?: {hasattr(package, attr)}")
        
except Exception as e:
    import traceback
    traceback.print_exc()
