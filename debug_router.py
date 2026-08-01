"""Debug: test the router endpoints directly."""
from fastapi.testclient import TestClient
from src.routers.constraints import router

client = TestClient(router, raise_server_exceptions=False)

resp = client.get("/api/v1/constraints")
print(f"GET /api/v1/constraints: {resp.status_code}")
if resp.status_code != 200:
    print(resp.text[:500])
else:
    data = resp.json()
    print(f"Platforms: {list(data.get('platforms', {}).keys())}")

resp2 = client.get("/api/v1/constraints/twitter")
print(f"\nGET /api/v1/constraints/twitter: {resp2.status_code}")
if resp2.status_code != 200:
    print(resp2.text[:500])
else:
    print(f"display_name: {resp2.json().get('display_name')}")

resp3 = client.post("/api/v1/validate", json={"platforms": ["twitter"], "text": "Hello"})
print(f"\nPOST /api/v1/validate: {resp3.status_code}")
if resp3.status_code != 200:
    print(resp3.text[:500])
else:
    print(f"valid: {resp3.json().get('valid')}")
