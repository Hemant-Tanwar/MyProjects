from pycelonis import get_celonis

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

def test_conn():
    try:
        print("Connecting to Celonis...")
        celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
        p = celonis.data_integration.get_data_pools()[0]
        print("Data Pool ID:", p.id)
        
        # Make a POST request to create a connection
        payload = {
            "name": "Data_source",
            "type": "FILES"  # File upload connection type
        }
        print("Sending request to create connection...")
        # PyCelonis core client request relative URL or absolute
        resp = celonis.client.request("POST", f"integration/api/pools/{p.id}/connections", json=payload)
        print("Response:", resp)
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_conn()
