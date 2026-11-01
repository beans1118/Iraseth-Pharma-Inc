def test_health(client):
    r = client.get('/api/health')
    assert r.status_code == 200 and r.get_json()['status'] == 'ok'


def test_ready(client):
    r = client.get('/api/ready')
    assert r.status_code == 200 and r.get_json()['database'] == 'ok'


def test_database_isolation(test_db):
    assert test_db.name == 'iraseth_test'
