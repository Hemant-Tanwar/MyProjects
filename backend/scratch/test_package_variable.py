from pycelonis import get_celonis
import json

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
spaces = celonis.studio.get_spaces()
if not spaces:
    print("No spaces found!")
    exit(1)

space = spaces[0]
packages = space.get_packages()
if not packages:
    print("No packages found!")
    exit(1)

p = packages[0]
print(f"Testing on Space: {space.name}, Package: {p.name}")

# Get existing variables
vars_list = p.get_variables()
print("Existing variables:", [v.key for v in vars_list])

# Test creating or updating a variable
var_key = "data-model"
# Let's delete if it exists
for v in vars_list:
    if v.key == var_key:
        print(f"Deleting existing variable {var_key}")
        v.delete()

# Create variable
print("Creating variable...")
new_var = p.create_variable(key=var_key, value="dummy-dm-id", type_="DATA_MODEL", runtime=False)
print(f"Created variable: key={new_var.key}, value={new_var.value}, type={new_var.type_}")
