"""Read-only and validation-only order tests. No actual customer emails are sent."""
def test_orders_requires_auth(client):
    assert client.get('/api/orders').status_code == 401


def test_orders_invalid_pagination(client, auth):
    r = client.get('/api/orders?page=not-a-number', headers=auth())
    assert r.status_code == 400


def test_order_missing_required_fields(client):
    r = client.post('/api/orders', json={})
    assert r.status_code == 400


def test_order_unknown_product(client):
    r = client.post('/api/orders', json={
        'client':'Test Customer', 'email':'pytest@example.invalid', 'facility':'Testing Facility',
        'lines':[{'id':'PYTEST-NO-SUCH-PRODUCT', 'qty':1}]
    })
    assert r.status_code == 400
