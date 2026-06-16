from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")

print("Deleting existing Order to Cash O2C data pool...")
for p in c.data_integration.get_data_pools():
    if p.name == "Order to Cash O2C":
        print(f"Deleting Data Pool: {p.name}")
        try:
            p.delete()
            print("Data Pool deleted successfully.")
        except Exception as e:
            print("Failed to delete data pool:", e)

print("\nDeleting existing Order to Cash O2C Space...")
for s in c.studio.get_spaces():
    if s.name == "Order to Cash O2C Space":
        print(f"Deleting Space: {s.name}")
        try:
            s.delete()
            print("Space deleted successfully.")
        except Exception as e:
            print("Failed to delete space:", e)

print("Clean-up complete!")
