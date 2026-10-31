def test_product_requires_login(client):
    assert client.get('/api/products').status_code == 401


def test_product_read_and_pagination(client, auth, product_factory):
    pid = product_factory()
    h = auth()
    r = client.get(f'/api/products/{pid}', headers=h)
    assert r.status_code == 200 and r.get_json()['id'] == pid
    r = client.get('/api/products?page=1&limit=2', headers=h)
    assert r.status_code == 200 and 'X-Total-Count' in r.headers


def test_subadmin_cannot_create_products(client, auth):
    r = client.post('/api/products', headers=auth('subadmin'), json={})
    assert r.status_code == 403


def test_negative_opening_quantity_rejected(client, auth):
    import uuid
    payload = {"id": "PYTEST-"+uuid.uuid4().hex, "name":"Sample", "description":"Sample",
               "category":"testing", "unit":"pcs", "quantity":-1}
    r = client.post('/api/products', headers=auth('superadmin'), json=payload)
    assert r.status_code == 400
