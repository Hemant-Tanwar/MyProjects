import kagglehub
import os

print("Downloading dataset...")
path = kagglehub.dataset_download("mustafakeser4/sap-dataset-bigquery-dataset")
print("Downloaded dataset to:", path)

if os.path.exists(path):
    print("Files in path:")
    for root, dirs, files in os.walk(path):
        for f in files:
            full_p = os.path.join(root, f)
            print(f" - {os.path.relpath(full_p, path)} (Size: {os.path.getsize(full_p)} bytes)")
else:
    print("Path does not exist!")
