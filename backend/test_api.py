from fastapi.testclient import TestClient
from database import init_db
from main import app


init_db()
client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

import time

def test_auth_and_flow():
    unique_email = f"testmgr_{int(time.time())}@stocksense.com"
    # Register
    reg_resp = client.post("/api/auth/register", json={
        "name": "Test Manager",
        "email": unique_email,
        "password": "secretpassword123"
    })
    assert reg_resp.status_code == 201

    # Login
    login_resp = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "secretpassword123"
    })
    assert login_resp.status_code == 200

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_cat_resp = client.post("/api/categories", json={"name": "Electronics", "description": "Gadgets and tech"}, headers=headers)
    assert create_cat_resp.status_code == 201




    # Fetch Categories
    cat_resp = client.get("/api/categories", headers=headers)
    assert cat_resp.status_code == 200
    assert len(cat_resp.json()) > 0


    # Fetch Dashboard KPIs
    kpi_resp = client.get("/api/dashboard/kpis", headers=headers)
    assert kpi_resp.status_code == 200
    assert "total_products" in kpi_resp.json()["kpis"]


if __name__ == "__main__":
    test_health()
    test_auth_and_flow()
    print("All integration tests passed successfully!")
