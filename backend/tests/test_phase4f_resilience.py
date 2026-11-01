"""Phase 4F integration tests. Requires isolated iraseth_test and MongoDB rs0.

Requires existing tests/conftest.py fixtures and current opt-in batch engine.
Never targets iraseth_dev or production data.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from config import Config
from modules.inventory import service


def key():
    return 'p4f-' + uuid4().hex


@pytest.fixture
def stock(monkeypatch, test_db, client, auth):
    assert test_db.name == 'iraseth_test'
    monkeypatch.setattr(Config, 'BATCH_MODE', True)
    pid = 'P4F-' + uuid4().hex
    test_db.products.insert_one({'id': pid, 'name': 'Hardening test product', 'quantity': 0,
                                 'baseline_qty': 0, 'category': 'testing', 'unit': 'pcs', 'price': 1})
    headers = auth('superadmin')
    keys = []
    orders = []
    def request(path, payload=None, *, operation_key=None):
        k = operation_key or key()
        keys.append(k)
        return client.post(path, json=payload or {}, headers={**headers, 'Idempotency-Key': k})
    def make_order(qty):
        oid = 'P4F-ORDER-' + uuid4().hex
        test_db.orders.insert_one({'id': oid, 'status': 'Pending', 'lines': [{'id': pid, 'qty': qty}]})
        orders.append(oid)
        return oid
    try:
        yield {'db': test_db, 'pid': pid, 'headers': headers, 'request': request, 'order': make_order,
               'keys': keys, 'orders': orders}
    finally:
        # This fixture removes only documents associated with its generated identifiers.
        test_db.stock_reservations.delete_many({'order_id': {'$in': orders}})
        test_db.orders.delete_many({'id': {'$in': orders}})
        batches = [b['id'] for b in test_db.inventory_batches.find({'product_id': pid}, {'id': 1})]
        test_db.inventory_adjustments.delete_many({'batch_id': {'$in': batches}})
        test_db.stock_movements.delete_many({'product_id': pid})
        test_db.inventory_batches.delete_many({'product_id': pid})
        test_db.inventory_operations.delete_many({'key': {'$in': keys}})
        test_db.products.delete_one({'id': pid})


def receive(stock, qty=10):
    r = stock['request']('/api/v2/inventory/batches/receive', {
        'product_id': stock['pid'], 'lot': 'P4F-LOT',
        'expires_on': (date.today() + timedelta(days=90)).isoformat(), 'qty': qty})
    assert r.status_code == 201, (r.status_code, r.get_json())
    return r.get_json()


def balances(stock):
    db, pid = stock['db'], stock['pid']
    product = db.products.find_one({'id': pid})
    batches = list(db.inventory_batches.find({'product_id': pid}))
    assert product['quantity'] == sum(b['on_hand'] for b in batches)
    assert all(isinstance(b['on_hand'], int) and isinstance(b['reserved'], int) and
               0 <= b['reserved'] <= b['on_hand'] for b in batches)
    return product['quantity']


def test_same_key_never_receives_twice(stock):
    shared = key()
    payload = {'product_id': stock['pid'], 'lot': 'P4F-LOT',
               'expires_on': (date.today() + timedelta(days=90)).isoformat(), 'qty': 10}
    first = stock['request']('/api/v2/inventory/batches/receive', payload, operation_key=shared)
    assert first.status_code == 201, first.get_json()
    again = stock['request']('/api/v2/inventory/batches/receive', payload, operation_key=shared)
    assert again.status_code in (400, 409), (again.status_code, again.get_json())
    assert balances(stock) == 10
    assert stock['db'].stock_movements.count_documents({'product_id': stock['pid'], 'action': 'receive'}) == 1


def test_audit_failure_rolls_back_receipt(stock):
    pid = stock['pid']
    # Patch only movement writer, after operation / batch / product mutations have been attempted.
    operation_key = key()
    stock['keys'].append(operation_key)
    with patch.object(service, 'movement', side_effect=RuntimeError('simulated movement failure')):
        with pytest.raises(RuntimeError, match='simulated movement failure'):
            service.receive(pid, 'ROLLBACK', (date.today() + timedelta(days=60)).isoformat(),
                            7, 'pytest@example.invalid', operation_key)
    assert balances(stock) == 0
    assert stock['db'].inventory_batches.count_documents({'product_id': pid}) == 0
    assert stock['db'].stock_movements.count_documents({'product_id': pid}) == 0


def test_audit_failure_rolls_back_release(stock):
    receive(stock, 10)
    pid = stock['pid']
    count_before = stock['db'].stock_movements.count_documents({'product_id': pid})
    operation_key = key()
    stock['keys'].append(operation_key)
    with patch.object(service, 'movement', side_effect=RuntimeError('simulated movement failure')):
        with pytest.raises(RuntimeError, match='simulated movement failure'):
            service.manual_release(pid, 3, 'pytest@example.invalid', operation_key, 'rollback test')
    assert balances(stock) == 10
    assert stock['db'].stock_movements.count_documents({'product_id': pid}) == count_before
    assert stock['db'].inventory_batches.find_one({'product_id': pid})['reserved'] == 0


def test_concurrent_releases_never_overdraw(stock):
    receive(stock, 10)
    pid = stock['pid']
    barrier = Barrier(2)
    def release(_):
        barrier.wait(timeout=10)
        try:
            operation_key = key()
            stock['keys'].append(operation_key)
            service.manual_release(pid, 7, 'pytest@example.invalid', operation_key, 'concurrent test')
            return 'ok'
        except service.InventoryProblem:
            return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(release, range(2)))
    assert outcomes.count('ok') == 1, outcomes
    assert outcomes.count('rejected') == 1, outcomes
    assert balances(stock) == 3
    assert stock['db'].stock_movements.count_documents({'product_id': pid, 'action': 'manual_release'}) == 1


def test_concurrent_approvals_cannot_oversubscribe(stock):
    receive(stock, 10)
    first = stock['order'](7)
    second = stock['order'](7)
    barrier = Barrier(2)
    def approve(oid):
        barrier.wait(timeout=10)
        try:
            operation_key = key()
            stock['keys'].append(operation_key)
            service.reserve_order(oid, 'pytest@example.invalid', operation_key)
            return 'ok'
        except service.InventoryProblem:
            return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(approve, [first, second]))
    assert sorted(outcomes) == ['ok', 'rejected'], outcomes
    assert balances(stock) == 10
    batch = stock['db'].inventory_batches.find_one({'product_id': stock['pid']})
    assert batch['reserved'] == 7
    active = list(stock['db'].stock_reservations.find({'order_id': {'$in': [first, second]}, 'status': 'active'}))
    assert sum(r['qty'] for r in active) == 7


def test_approval_shortage_rolls_back_all_reservations(stock):
    receive(stock, 5)
    oid = stock['order'](6)
    result = stock['request'](f'/api/v2/orders/{oid}/approve')
    assert result.status_code in (400, 409), (result.status_code, result.get_json())
    assert stock['db'].orders.find_one({'id': oid})['status'] == 'Pending'
    assert stock['db'].stock_reservations.count_documents({'order_id': oid}) == 0
    assert stock['db'].inventory_batches.find_one({'product_id': stock['pid']})['reserved'] == 0
    assert balances(stock) == 5


def test_cross_collection_reconciliation_detects_corruption(stock):
    from modules.inventory.readiness import check_ready
    receive(stock, 5)
    assert check_ready(stock['db'], require_marker=False) is True
    stock['db'].products.update_one({'id': stock['pid']}, {'$inc': {'quantity': 1}})
    try:
        with pytest.raises(RuntimeError, match='mismatch'):
            check_ready(stock['db'], require_marker=False)
    finally:
        stock['db'].products.update_one({'id': stock['pid']}, {'$inc': {'quantity': -1}})
    assert balances(stock) == 5
