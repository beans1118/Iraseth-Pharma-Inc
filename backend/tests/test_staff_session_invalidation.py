"""Extra tests: staff lifecycle routes revoke existing sessions."""


def test_role_change_via_api_revokes_target_session(client, auth, accounts, test_db):
    super_headers = auth("superadmin")
    sub_headers = auth("subadmin")
    target = accounts["subadmin"]["email"]
    assert client.get("/api/auth/me", headers=sub_headers).status_code == 200

    response = client.patch(
        f"/api/users/{target}", json={"role": "admin"}, headers=super_headers
    )
    assert response.status_code == 200, response.get_json()
    assert client.get("/api/auth/me", headers=sub_headers).status_code == 401
    assert test_db.sessions.count_documents({"user_email": target, "logout_at": None}) == 0


def test_deletion_via_api_revokes_target_session(client, auth, accounts, test_db):
    super_headers = auth("superadmin")
    sub_headers = auth("subadmin")
    target = accounts["subadmin"]["email"]
    response = client.delete(f"/api/users/{target}", headers=super_headers)
    assert response.status_code == 200, response.get_json()
    assert client.get("/api/auth/me", headers=sub_headers).status_code == 401
    assert test_db.sessions.count_documents({"user_email": target, "logout_at": None}) == 0
