def test_product_requires_login(client):
    assert client.get('/api/products').status_code == 401


def test_product_read_and_pagination(client, auth, product_factory):
    pid = product_factory()
    h = auth()
    r = client.get(f'/api/products/{pid}', headers=h)
    assert r.status_code == 200 and r.get_json()['id'] == pid
    r = client.get('/api/products?page=1&limit=2', headers=h)
    assert r.status_code == 200 and 'X-Total-Count' in r.headers


def test_subadmin_can_access_create_product_validation(client, auth):
    """Sub-admin can create products, but an empty payload is invalid."""
    r = client.post('/api/products', headers=auth('subadmin'), json={})
    assert r.status_code == 400


def test_board_admin_cannot_create_products(client, auth):
    """Board Admin retains read-only access, even with an invalid payload."""
    r = client.post('/api/products', headers=auth('admin'), json={})
    assert r.status_code == 403


def test_negative_opening_quantity_rejected(client, auth):
    import uuid
    payload = {"id": "PYTEST-"+uuid.uuid4().hex, "name":"Sample", "description":"Sample",
               "category":"testing", "unit":"pcs", "quantity":-1}
    r = client.post('/api/products', headers=auth('superadmin'), json=payload)
    assert r.status_code == 400
