"""Isolated iraseth_test integration coverage; only fixture-owned documents are removed."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from test_quotations_phase3 import setup_product, payload


@pytest.fixture
def inquiry(client, test_db, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, 'BATCH_MODE', True)
    # Separate rate-limit principal so these tests do not exhaust other tests' buckets.
    client.environ_base['REMOTE_ADDR'] = 'pytest-' + uuid4().hex
    pid = setup_product(test_db)
    test_db.products.update_one({'id': pid}, {'$set': {'price': 12.5, 'unit': 'Box'}})
    key = uuid4().hex
    ref = None
    try:
        result = client.post('/api/public/quotations', json=payload(pid), headers={'Idempotency-Key': key})
        assert result.status_code == 201, result.get_json()
        ref = result.get_json()['reference']
        yield pid, ref, key
    finally:
        test_db.orders.delete_many({'source_inquiry_id': ref})
        test_db.quotation_events.delete_many({'reference': ref})
        test_db.quotations.delete_many({'idempotency_key': key})
        test_db.inventory_batches.delete_many({'product_id': pid})
        test_db.products.delete_many({'id': pid})


def test_retry_survives_catalog_changes_and_legacy_hash(client, test_db, inquiry):
    pid, ref, key = inquiry
    test_db.quotations.update_one({'id': ref}, {'$set': {'payload_hash': 'legacy-snapshot-hash'}})
    test_db.products.update_one({'id': pid}, {'$set': {'storefront_visible': False, 'storefront_price': 999}})
    test_db.inventory_batches.update_one({'product_id': pid}, {'$set': {'on_hand': 0}})
    result = client.post('/api/public/quotations', json=payload(pid), headers={'Idempotency-Key': key})
    assert result.status_code == 200
    assert result.get_json()['reference'] == ref
    changed = payload(pid); changed['notes'] = 'Changed intent'
    assert client.post('/api/public/quotations', json=changed, headers={'Idempotency-Key': key}).status_code == 409
    assert test_db.quotations.count_documents({'idempotency_key': key}) == 1


def test_accept_creates_one_pending_order_without_stock_changes(client, auth, test_db, inquiry):
    pid, ref, _ = inquiry
    headers = auth('subadmin')
    batch = test_db.inventory_batches.find_one({'product_id': pid})
    product = test_db.products.find_one({'id': pid})
    reservations = test_db.stock_reservations.count_documents({})
    movements = test_db.stock_movements.count_documents({})
    invoices = test_db.invoices.count_documents({})
    first = client.post(f'/api/v2/quotations/{ref}/accept', headers=headers)
    assert first.status_code == 200, first.get_json()
    oid = first.get_json()['order_id']
    assert client.post(f'/api/v2/quotations/{ref}/accept', headers=headers).get_json()['order_id'] == oid
    assert client.patch(f'/api/v2/quotations/{ref}/status', headers=headers, json={'status': 'Accepted'}).get_json()['order_id'] == oid
    order = test_db.orders.find_one({'id': oid})
    assert order['status'] == 'Pending'
    assert (order['client'], order['email'], order['facility'], order['phone']) == ('Sample Customer', 'sample@example.org', 'Sample Clinic', '09000000000')
    assert order['lines'][0]['qty'] == 2
    assert order['lines'][0]['price'] == 12.5
    assert order['total'] == 25
    assert order['notes'][0]['text'] == 'Please advise lead time'
    assert test_db.quotations.find_one({'id': ref})['items'][0]['public_price_at_inquiry'] == 125.5
    assert test_db.orders.count_documents({'source_inquiry_id': ref}) == 1
    assert test_db.quotation_events.count_documents({'reference': ref}) == 1
    assert test_db.inventory_batches.find_one({'product_id': pid}) == batch
    assert test_db.products.find_one({'id': pid}) == product
    assert test_db.stock_reservations.count_documents({}) == reservations
    assert test_db.stock_movements.count_documents({}) == movements
    assert test_db.invoices.count_documents({}) == invoices
    assert client.get(f'/api/orders/{oid}', headers=auth('admin')).status_code == 200
    assert client.post(f'/api/v2/quotations/{ref}/decline', headers=headers).status_code == 409
    assert client.patch(f'/api/v2/quotations/{ref}/status', headers=headers, json={'status':'New'}).status_code == 409


@pytest.mark.parametrize('action', ['accept', 'decline'])
def test_decision_permissions(client, auth, inquiry, action):
    _, ref, _ = inquiry
    url = f'/api/v2/quotations/{ref}/{action}'
    assert client.post(url).status_code == 401
    assert client.post(url, headers=auth('admin')).status_code == 403
    assert client.patch(f'/api/v2/quotations/{ref}/status', headers=auth('admin'), json={'status':'Accepted'}).status_code == 403
    assert client.post(url, headers=auth('superadmin')).status_code == 200


def test_decline_is_terminal_and_creates_no_order(client, auth, test_db, inquiry):
    _, ref, _ = inquiry
    headers = auth('subadmin')
    assert client.post(f'/api/v2/quotations/{ref}/decline', headers=headers).status_code == 200
    assert client.post(f'/api/v2/quotations/{ref}/decline', headers=headers).status_code == 200
    assert client.post(f'/api/v2/quotations/{ref}/accept', headers=headers).status_code == 409
    assert test_db.orders.count_documents({'source_inquiry_id': ref}) == 0
    assert test_db.quotation_events.count_documents({'reference': ref}) == 1


def test_accept_rolls_back_if_audit_write_fails(client, auth, test_db, inquiry, monkeypatch):
    _, ref, _ = inquiry
    headers = auth('superadmin')
    original = type(test_db.quotation_events).insert_one
    def fail(collection, *args, **kwargs):
        if collection.name == 'quotation_events':
            raise RuntimeError('injected audit failure')
        return original(collection, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(type(test_db.quotation_events), 'insert_one', fail)
        with pytest.raises(RuntimeError, match='injected audit failure'):
            client.post(f'/api/v2/quotations/{ref}/accept', headers=headers)
    assert test_db.orders.count_documents({'source_inquiry_id': ref}) == 0
    assert test_db.quotations.find_one({'id': ref})['status'] == 'New'
    assert client.post(f'/api/v2/quotations/{ref}/accept', headers=headers).status_code == 200


def test_concurrent_accept_creates_one_order(client, auth, test_db, inquiry):
    from app import app
    _, ref, _ = inquiry
    headers = auth('superadmin')
    def accept(_):
        with app.test_client() as other:
            result = other.post(f'/api/v2/quotations/{ref}/accept', headers=headers)
            return result.status_code, result.get_json()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(accept, range(4)))
    assert all(code == 200 for code, _ in results), results
    assert len({body['order_id'] for _, body in results}) == 1
    assert test_db.orders.count_documents({'source_inquiry_id': ref}) == 1
    assert test_db.quotation_events.count_documents({'reference': ref}) == 1


def test_accept_missing_product_leaves_inquiry_unchanged(client, auth, test_db, inquiry):
    pid, ref, _ = inquiry
    test_db.products.delete_one({'id': pid})
    result = client.post(f'/api/v2/quotations/{ref}/accept', headers=auth('superadmin'))
    assert result.status_code == 409
    assert test_db.quotations.find_one({'id': ref})['status'] == 'New'
    assert test_db.orders.count_documents({'source_inquiry_id': ref}) == 0


def test_manual_orders_remain_independent(client, auth, test_db, inquiry, monkeypatch):
    import routes.orders as orders
    monkeypatch.setattr(orders, 'order_confirmation_email', lambda *a, **k: None)
    pid, ref, _ = inquiry
    manual = []
    try:
        # The partial unique inquiry index must allow multiple normal orders.
        for _ in range(2):
            result = client.post('/api/orders', json={'client':'Manual Customer',
                'email':'manual@example.invalid', 'facility':'Manual Clinic',
                'lines':[{'id':pid, 'qty':1}]})
            assert result.status_code == 201, result.get_json()
            manual.append(result.get_json()['id'])
        assert len(set(manual)) == 2
        assert all('source_inquiry_id' not in test_db.orders.find_one({'id':oid}) for oid in manual)
        assert client.post(f'/api/v2/quotations/{ref}/accept', headers=auth('superadmin')).status_code == 200
        assert all(test_db.orders.find_one({'id':oid})['status'] == 'Pending' for oid in manual)
    finally:
        test_db.orders.delete_many({'id': {'$in': manual}})


def test_concurrent_accept_decline_has_one_terminal_decision(client, auth, test_db, inquiry):
    from app import app
    _, ref, _ = inquiry
    headers = auth('subadmin')
    def decide(action):
        with app.test_client() as other:
            response = other.post(f'/api/v2/quotations/{ref}/{action}', headers=headers)
            return response.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(decide, ['accept', 'decline']))
    assert sorted(codes) == [200,409]
    q = test_db.quotations.find_one({'id':ref})
    assert q['status'] in ('Accepted','Declined')
    assert test_db.orders.count_documents({'source_inquiry_id':ref}) == (1 if q['status']=='Accepted' else 0)
    assert test_db.quotation_events.count_documents({'reference':ref}) == 1


def test_converted_order_uses_existing_approval_and_fulfillment(client, auth, test_db, inquiry):
    pid, ref, _ = inquiry
    headers = auth('superadmin')
    keys = [uuid4().hex, uuid4().hex]
    oid = None
    test_db.products.update_one({'id':pid}, {'$set':{'quantity':5}})
    try:
        result = client.post(f'/api/v2/quotations/{ref}/accept', headers=headers)
        assert result.status_code == 200
        oid = result.get_json()['order_id']
        assert test_db.inventory_batches.find_one({'product_id':pid})['reserved'] == 0
        approved = client.post(f'/api/v2/orders/{oid}/approve', headers={**headers,'Idempotency-Key':keys[0]})
        assert approved.status_code == 200, approved.get_json()
        assert test_db.inventory_batches.find_one({'product_id':pid})['reserved'] == 2
        fulfilled = client.post(f'/api/v2/orders/{oid}/fulfill', headers={**headers,'Idempotency-Key':keys[1]})
        assert fulfilled.status_code == 200, fulfilled.get_json()
        assert test_db.orders.find_one({'id':oid})['status'] == 'Fulfilled'
        batch = test_db.inventory_batches.find_one({'product_id':pid})
        assert (batch['on_hand'],batch['reserved']) == (3,0)
        assert test_db.products.find_one({'id':pid})['quantity'] == 3
    finally:
        test_db.inventory_operations.delete_many({'key':{'$in':keys}})
        test_db.stock_movements.delete_many({'product_id':pid})
        if oid:
            test_db.stock_reservations.delete_many({'order_id':oid})
