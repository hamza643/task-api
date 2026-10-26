from datetime import timedelta

from fastapi.testclient import TestClient

from main import app
from security import create_access_token

client = TestClient(app)

good = create_access_token("ali")
expired = create_access_token("ali", expires_delta=timedelta(minutes=-5))

r1 = client.get("/me", headers={"Authorization": f"Bearer {good}"})
r2 = client.get("/me", headers={"Authorization": f"Bearer {expired}"})
r3 = client.get("/me")

print("valid token  :", r1.status_code, r1.json())
print("expired token:", r2.status_code, r2.json())
print("no token     :", r3.status_code, r3.json())