
def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ok"


def test_ready_endpoint(client):
    response = client.get("/api/ready")

    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "ready"
    assert data["database"] == "ok"


def test_database_isolation(test_db):
    assert test_db.name == "iraseth_test"
