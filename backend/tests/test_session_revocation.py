"""Known gaps: role changes and account deletion must revoke old privileges."""
import pytest


@pytest.mark.xfail(strict=True, reason="Current auth checks session role, not current users.role")
def test_role_demotion_revokes_old_superadmin_token(client, auth, accounts, test_db):
    headers = auth("superadmin")
    email = accounts["superadmin"]["email"]
    assert client.get("/api/users", headers=headers).status_code == 200
    test_db.users.update_one({"email": email}, {"$set": {"role": "subadmin"}})
    # A token with previous superadmin privileges must no longer be accepted.
    response = client.get("/api/users", headers=headers)
    assert response.status_code in (401, 403), response.get_json()


@pytest.mark.xfail(strict=True, reason="Current auth checks active sessions but not deleted user accounts")
def test_deleted_user_token_is_rejected(client, auth, accounts, test_db):
    headers = auth("superadmin")
    email = accounts["superadmin"]["email"]
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    test_db.users.delete_one({"email": email})
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401, response.get_json()
