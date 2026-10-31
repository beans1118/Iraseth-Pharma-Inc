def test_login_and_me(client, accounts, auth):
    h = auth('superadmin')
    r = client.get('/api/auth/me', headers=h)
    assert r.status_code == 200
    assert r.get_json()['email'] == accounts['superadmin']['email']


def test_logout_revokes_session(client, auth):
    h = auth('superadmin')
    assert client.post('/api/auth/logout', headers=h).status_code == 200
    assert client.get('/api/auth/me', headers=h).status_code == 401


def test_subadmin_cannot_manage_users(client, auth):
    assert client.get('/api/users', headers=auth('subadmin')).status_code == 403


def test_superadmin_can_list_users(client, auth):
    assert client.get('/api/users', headers=auth('superadmin')).status_code == 200
