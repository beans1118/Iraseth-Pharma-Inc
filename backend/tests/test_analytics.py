"""Analytics endpoint security and validation, using the isolated test database."""

def test_analytics_requires_staff_authentication(client):
    response = client.get('/api/v2/analytics/overview')
    assert response.status_code in (401, 403)

def test_analytics_rejects_bad_period(client, auth):
    response = client.get('/api/v2/analytics/overview?days=365', headers=auth())
    assert response.status_code == 400

def test_analytics_returns_live_schema(client, auth):
    response = client.get('/api/v2/analytics/overview?days=7', headers=auth())
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data['period_days'] == 7
    assert isinstance(data['products'], int)
    assert isinstance(data['orders_by_status'], dict)
    assert isinstance(data['invoices_by_status'], dict)
    assert isinstance(data['movement_trends'], list)
