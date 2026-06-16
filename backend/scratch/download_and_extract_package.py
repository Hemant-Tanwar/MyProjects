from pycelonis import get_celonis
import zipfile
import io
import os
import shutil

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
space = [s for s in c.studio.get_spaces() if "Procurement" in s.name][0]
package = [p for p in space.get_packages() if p.key == "procurement-process-optimization-2363b3c3"][0]

export_path = "pkg_export_temp.zip"
print(f"Exporting package {package.key}...")
package.download(export_path)

temp_dir = "extracted_pkg_temp"
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir)

with zipfile.ZipFile(export_path, 'r') as zip_ref:
    zip_ref.extractall(temp_dir)

print("\nFiles in package:")
for root, dirs, files in os.walk(temp_dir):
    for file in files:
        rel_path = os.path.relpath(os.path.join(root, file), temp_dir)
        print(" -", rel_path)
        if rel_path.endswith(".yml") or rel_path.endswith(".yaml") or rel_path.endswith(".json"):
            print(f"=== {rel_path} ===")
            with open(os.path.join(root, file), 'r') as f:
                print(f.read())
            print("=" * 40)

# Cleanup
shutil.rmtree(temp_dir)
os.remove(export_path)
