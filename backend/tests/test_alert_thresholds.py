from modules.alerts.routes import compute_watchlist


def test_per_product_override_and_fallback():
    products = [
        {'id': 'A', 'name': 'A', 'unit': 'box', 'min_stock_threshold': 3},
        {'id': 'B', 'name': 'B', 'unit': 'box'},
        {'id': 'C', 'name': 'C', 'unit': 'box', 'min_stock_threshold': 0},
    ]
    batches = [
        {'id': '1', 'product_id': 'A', 'lot': 'a', 'on_hand': 5, 'reserved': 0, 'condition': 'available', 'expires_on': '2026-12-01'},
        {'id': '2', 'product_id': 'B', 'lot': 'b', 'on_hand': 5, 'reserved': 0, 'condition': 'available', 'expires_on': '2026-12-01'},
        {'id': '3', 'product_id': 'C', 'lot': 'c', 'on_hand': 5, 'reserved': 0, 'condition': 'available', 'expires_on': '2026-12-01'},
    ]
    result = compute_watchlist(products, batches, '2026-11-01', 30, 10)
    assert [p['product_id'] for p in result['low_stock']] == ['B']
    thresholds = {p['product_id']: p['threshold'] for p in result['all_products']}
    assert thresholds == {'A': 3, 'B': 10, 'C': 0}


def test_threshold_patch_permissions_and_validation(client, auth):
    assert client.patch('/api/v2/alerts/products/nonexistent/threshold', json={'threshold': 7}).status_code in (401,403)
    url = '/api/v2/alerts/products/nonexistent/threshold'
    assert client.patch(url, headers=auth('subadmin'), json={'threshold': 7}).status_code == 403
    assert client.patch(url, headers=auth(), json={'threshold': True}).status_code == 400
    assert client.patch(url, headers=auth(), json={'threshold': -1}).status_code == 400
    assert client.patch(url, headers=auth(), json={'threshold': 1.5}).status_code == 400
    assert client.patch(url, headers=auth(), json={'threshold': 100001}).status_code == 400
    assert client.patch(url, headers=auth(), json={'threshold': 10}).status_code == 404
