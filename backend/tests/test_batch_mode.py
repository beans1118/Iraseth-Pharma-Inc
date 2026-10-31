"""Batch mode contract and data safety checks. Require local iraseth_test DB."""
import uuid

_USED_KEYS = []
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from config import Config
from extensions import db
from modules.inventory.service import InventoryProblem, receive, manual_release, reserve_order, fulfill_reserved


@pytest.fixture
def batch_mode(monkeypatch, test_db):
    assert test_db.name == 'iraseth_test'
    monkeypatch.setattr(Config, 'BATCH_MODE', True)
    created_products = []
    initial_key_index = len(_USED_KEYS)
    created_orders = []
    def add_product(qty=0):
        pid = 'BATCH-TEST-' + uuid.uuid4().hex
        test_db.products.insert_one({'id': pid, 'name': pid, 'quantity': qty, 'unit': 'pcs', 'price': 1})
        created_products.append(pid)
        return pid
    def add_order(lines):
        oid = 'BATCH-ORDER-' + uuid.uuid4().hex
        test_db.orders.insert_one({'id': oid, 'status': 'Pending', 'lines': lines})
        created_orders.append(oid)
        return oid
    yield add_product, add_order
    # Cleanup only documents attributable to this fixture's test IDs.
    test_db.stock_reservations.delete_many({'order_id': {'$in': created_orders}})
    test_db.orders.delete_many({'id': {'$in': created_orders}})
    test_db.stock_movements.delete_many({'product_id': {'$in': created_products}})
    batch_ids = [b['id'] for b in test_db.inventory_batches.find({'product_id': {'$in': created_products}}, {'id': 1})]
    test_db.inventory_adjustments.delete_many({'batch_id': {'$in': batch_ids}})
    test_db.inventory_operations.delete_many({'key': {'$in': _USED_KEYS[initial_key_index:]}})
    del _USED_KEYS[initial_key_index:]
    test_db.inventory_batches.delete_many({'product_id': {'$in': created_products}})
    test_db.products.delete_many({'id': {'$in': created_products}})
    # Each test uses its own key prefix, so cleanup is explicit per test below.


def key():
    value = 'pytest-' + uuid.uuid4().hex
    _USED_KEYS.append(value)
    return value


def expires(days=100):
    return (date.today() + timedelta(days=days)).isoformat()


def test_disabled_v2_endpoints(client):
    assert client.get('/api/v2/inventory/batches').status_code == 401


def test_receipt_and_manual_release_fefo(batch_mode, test_db):
    product, _ = batch_mode
    pid = product()
    first = receive(pid, 'EARLY', expires(25), 5, 'pytest@example.invalid', key())
    later = receive(pid, 'LATE', expires(80), 5, 'pytest@example.invalid', key())
    released = manual_release(pid, 7, 'pytest@example.invalid', key(), 'warehouse release')
    assert [x['qty'] for x in released['allocations']] == [5, 2]
    assert released['allocations'][0]['batch_id'] == first['id']
    assert test_db.inventory_batches.find_one({'id': first['id']})['on_hand'] == 0
    assert test_db.inventory_batches.find_one({'id': later['id']})['on_hand'] == 3
    assert test_db.products.find_one({'id': pid})['quantity'] == 3


def test_no_release_of_expired_batch(batch_mode, test_db):
    product, _ = batch_mode
    pid = product()
    # Simulate a pre-existing expired batch with restricted stock.
    test_db.inventory_batches.insert_one({'id': uuid.uuid4().hex, 'product_id': pid,
        'lot': 'OLD', 'expires_on': expires(-1), 'condition': 'available',
        'unverified': False, 'on_hand': 10, 'reserved': 0})
    with pytest.raises(InventoryProblem):
        manual_release(pid, 1, 'pytest@example.invalid', key(), 'test')


def test_approved_order_reserves_and_fulfills(batch_mode, test_db):
    product, order = batch_mode
    pid = product()
    batch = receive(pid, 'LOT-X', expires(), 10, 'pytest@example.invalid', key())
    oid = order([{'id': pid, 'qty': 4}])
    approved = reserve_order(oid, 'pytest@example.invalid', key())
    assert approved['status'] == 'Approved'
    assert test_db.inventory_batches.find_one({'id': batch['id']})['reserved'] == 4
    with pytest.raises(InventoryProblem):
        manual_release(pid, 7, 'pytest@example.invalid', key(), 'too much')
    assert fulfill_reserved(oid, 'pytest@example.invalid', key())['status'] == 'Fulfilled'
    after = test_db.inventory_batches.find_one({'id': batch['id']})
    assert (after['on_hand'], after['reserved']) == (6, 0)
    assert test_db.products.find_one({'id': pid})['quantity'] == 6
    with pytest.raises(InventoryProblem):
        fulfill_reserved(oid, 'pytest@example.invalid', key())


def test_batch_mode_blocks_legacy_inventory(client, batch_mode, auth):
    headers = auth('superadmin')
    assert client.get('/api/inventory', headers=headers).status_code == 409
    assert client.post('/api/inventory/whatever/supply', json={'qty': 1}, headers=headers).status_code == 409


def test_adjustment_request_needs_superadmin_approval(batch_mode, test_db):
    from modules.inventory.service import request_adjustment, decide_adjustment
    product, _ = batch_mode
    pid = product()
    batch = receive(pid, 'ADJUST', expires(), 9, 'pytest@example.invalid', key())
    adjustment = request_adjustment(batch['id'], -2, 'count mismatch', 'requester@example.invalid')
    assert test_db.inventory_batches.find_one({'id': batch['id']})['on_hand'] == 9
    approved = decide_adjustment(adjustment['id'], True, 'reviewer@example.invalid', key())
    assert approved['status'] == 'approved'
    assert test_db.inventory_batches.find_one({'id': batch['id']})['on_hand'] == 7
    assert test_db.products.find_one({'id': pid})['quantity'] == 7


def test_cancellation_releases_reserved_stock(batch_mode, test_db):
    from modules.inventory.service import cancel_order
    product, order = batch_mode
    pid = product()
    batch = receive(pid, 'CANCEL', expires(), 6, 'pytest@example.invalid', key())
    oid = order([{'id': pid, 'qty': 4}])
    reserve_order(oid, 'pytest@example.invalid', key())
    cancel_order(oid, 'pytest@example.invalid', key())
    assert test_db.inventory_batches.find_one({'id': batch['id']})['reserved'] == 0
    assert test_db.orders.find_one({'id': oid})['status'] == 'Cancelled'


def test_return_quarantined_and_disposal(batch_mode, test_db):
    from modules.inventory.service import receive_return, dispose
    product, order = batch_mode
    pid = product()
    receive(pid, 'SHIP', expires(), 5, 'pytest@example.invalid', key())
    oid = order([{'id': pid, 'qty': 3}])
    reserve_order(oid, 'pytest@example.invalid', key())
    fulfill_reserved(oid, 'pytest@example.invalid', key())
    returned = receive_return(oid, pid, 'SHIP', expires(), 2,
        'pytest@example.invalid', key(), 'customer return')
    quarantined = test_db.inventory_batches.find_one({'id': returned['batch_id']})
    assert quarantined['condition'] == 'quarantine'
    assert quarantined['on_hand'] == 2
    disposed = dispose(returned['batch_id'], 1, 'pytest@example.invalid', key(), 'damaged return')
    assert disposed['disposed'] == 1
    assert test_db.products.find_one({'id': pid})['quantity'] == 3


def test_duplicate_operation_key_rejected(batch_mode, test_db):
    product, _ = batch_mode
    pid = product()
    idem = key()
    receive(pid, 'DUP', expires(), 2, 'pytest@example.invalid', idem)
    with pytest.raises(InventoryProblem):
        receive(pid, 'DUP', expires(), 2, 'pytest@example.invalid', idem)
    assert test_db.products.find_one({'id': pid})['quantity'] == 2
