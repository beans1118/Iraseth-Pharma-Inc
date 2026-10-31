
def test_login_requires_credentials(client):
    response = client.post("/api/auth/login", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_invalid_login(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent-test-user@example.invalid",
            "password": "incorrect-password"
        }
    )

    assert response.status_code == 401
    assert "error" in response.get_json()


def test_protected_endpoint_without_token(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_protected_endpoint_with_invalid_token(client):
    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        }
    )

    assert response.status_code == 401


def test_inventory_requires_authentication(client):
    response = client.get("/api/inventory")

    assert response.status_code == 401
