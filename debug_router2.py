"""Debug: test the router endpoints with full exception output."""
from fastapi.testclient import TestClient
from src.routers.constraints import router

client = TestClient(router, raise_server_exceptions=True)

try:
    resp = client.get("/api/v1/constraints")
    print(f"GET /api/v1/constraints: {resp.status_code}")
except Exception as e:
    print(f"Exception on GET /api/v1/constraints: {type(e).__name__}: {e}")
