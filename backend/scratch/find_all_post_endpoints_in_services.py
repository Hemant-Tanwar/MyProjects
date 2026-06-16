import os
import importlib
import inspect

service_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/backend/.venv/lib/python3.9/site-packages/pycelonis/service"

print("=== Searching for post_ methods in pycelonis services ===")
for root, dirs, files in os.walk(service_dir):
    for f in files:
        if f.endswith(".py") and f != "__init__.py":
            module_path = os.path.relpath(os.path.join(root, f), service_dir)
            module_name = "pycelonis.service." + module_path.replace(os.sep, ".").replace(".py", "")
            try:
                mod = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(mod, inspect.isclass):
                    if name.endswith("Service"):
                        post_methods = [m for m in dir(obj) if m.startswith("post_") or "conn" in m or "source" in m]
                        if post_methods:
                            print(f"Class: {module_name}.{name}")
                            for pm in post_methods:
                                print(f" - {pm}")
            except Exception as e:
                pass
