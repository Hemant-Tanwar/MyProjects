import urllib.request
import json

session_id = '7c82907a-5340-41d6-8b93-873325168938'
url = f"http://127.0.0.1:8001/sessions/{session_id}/artifacts/analysis/push"
req = urllib.request.Request(url, method="POST")

try:
    print("Calling analysis push endpoint...")
    with urllib.request.urlopen(req, timeout=120) as resp:
        print("Response status code:", resp.status)
        print("Response content:")
        print(resp.read().decode('utf-8'))
        print("Push completed successfully!")
except Exception as e:
    print(f"Error: {e}")
