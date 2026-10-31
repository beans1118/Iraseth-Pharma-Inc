def test_empty_login(client):
    r = client.post('/api/auth/login', json={})
    assert r.status_code == 400


def test_invalid_login(client):
    r = client.post('/api/auth/login', json={'email':'nobody@example.invalid','password':'wrong'})
    assert r.status_code == 401


def test_missing_token(client):
    assert client.get('/api/auth/me').status_code == 401


def test_invalid_token(client):
    assert client.get('/api/auth/me', headers={'Authorization':'Bearer bad-token'}).status_code == 401


def test_inventory_requires_login(client):
    assert client.get('/api/inventory').status_code == 401
