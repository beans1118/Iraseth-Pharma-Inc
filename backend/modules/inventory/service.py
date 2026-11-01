"""Batch inventory domain operations. All mutations run in MongoDB transactions.

Not enabled until reconciliation and BATCH_MODE=enabled. No Flask globals are
used here; actor identity is passed explicitly by authenticated route handlers.
"""
from collections import defaultdict
from datetime import date, datetime, timezone
from uuid import uuid4
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure
from extensions import db


class InventoryProblem(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat()


def positive(value):
    if isinstance(value, bool):
        raise InventoryProblem('Quantity must be a positive whole number.', 400)
    try:
        quantity = int(value)
    except (TypeError, ValueError, OverflowError):
        raise InventoryProblem('Quantity must be a positive whole number.', 400)
    if quantity <= 0 or str(value).strip() != str(quantity):
        raise InventoryProblem('Quantity must be a positive whole number.', 400)
    return quantity


def signed(value):
    if isinstance(value, bool):
        raise InventoryProblem('Adjustment must be a nonzero whole number.', 400)
    try:
        quantity = int(value)
    except (TypeError, ValueError, OverflowError):
        raise InventoryProblem('Adjustment must be a nonzero whole number.', 400)
    if quantity == 0 or str(value).strip() != str(quantity):
        raise InventoryProblem('Adjustment must be a nonzero whole number.', 400)
    return quantity


def expiry(value):
    try:
        result = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise InventoryProblem('Expiry must be YYYY-MM-DD.', 400)
    if result.isoformat() != value:
        raise InventoryProblem('Expiry must be YYYY-MM-DD.', 400)
    return value


def clean(document):
    if document is None:
        return None
    copy = dict(document)
    copy.pop('_id', None)
    return copy


def transaction(callback):
    try:
        with db.client.start_session() as session:
            return session.with_transaction(callback)
    except DuplicateKeyError as exc:
        raise InventoryProblem('Duplicate operation, batch, or request.', 409) from exc
    except OperationFailure as exc:
        if exc.has_error_label('TransientTransactionError'):
            raise InventoryProblem('Concurrent inventory update; retry request.', 409) from exc
        raise


def operation(session, kind, key, actor):
    if not isinstance(key, str) or not 8 <= len(key) <= 128:
        raise InventoryProblem('Idempotency-Key header must contain 8–128 characters.', 400)
    doc = {'id': uuid4().hex, 'key': key, 'kind': kind,
           'actor_email': actor, 'at': now()}
    db.inventory_operations.insert_one(doc, session=session)
    return doc['id']


def movement(session, batch, action, quantity, before, after, actor, reference, op_id):
    db.stock_movements.insert_one({
        'id': uuid4().hex, 'operation_id': op_id, 'batch_id': batch['id'],
        'product_id': batch['product_id'], 'lot': batch['lot'],
        'action': action, 'qty': quantity, 'before': before, 'after': after,
        'actor_email': actor, 'reference': reference, 'at': now()
    }, session=session)


def get_batch(session, batch_id):
    batch = db.inventory_batches.find_one({'id': batch_id}, session=session)
    if not batch:
        raise InventoryProblem('Batch not found.', 404)
    return batch


def ensure_eligible(batch):
    if batch['condition'] != 'available' or batch.get('unverified'):
        raise InventoryProblem('Batch is not eligible for release.')
    if batch['expires_on'] < date.today().isoformat():
        raise InventoryProblem('Batch has expired and cannot be released.')


def receive(product_id, lot, expires_on, quantity, actor, key, condition='available', reference='manual receipt'):
    quantity = positive(quantity)
    expires_on = expiry(expires_on)
    if not isinstance(lot, str) or not lot.strip() or len(lot) > 100:
        raise InventoryProblem('A lot number is required (max 100 characters).', 400)
    if condition not in ('available', 'quarantine'):
        raise InventoryProblem('Invalid receiving condition.', 400)
    if condition == 'available' and expires_on < date.today().isoformat():
        raise InventoryProblem('Cannot receive expired stock as available.', 409)

    def run(session):
        op_id = operation(session, 'receive', key, actor)
        if not db.products.find_one({'id': product_id}, {'_id': 1}, session=session):
            raise InventoryProblem('Product not found.', 404)
        batch = db.inventory_batches.find_one_and_update(
            {'product_id': product_id, 'lot': lot.strip(), 'expires_on': expires_on,
             'condition': condition, 'unverified': False},
            {'$inc': {'on_hand': quantity}, '$setOnInsert': {'id': uuid4().hex,
                'reserved': 0, 'created_at': now(), 'unverified': False}},
            upsert=True, return_document=ReturnDocument.AFTER, session=session)
        db.products.update_one({'id': product_id}, {'$inc': {'quantity': quantity}}, session=session)
        movement(session, batch, 'receive', quantity,
                 batch['on_hand'] - quantity, batch['on_hand'], actor, reference, op_id)
        return clean(batch)
    return transaction(run)


def allocate(session, product_id, qty):
    """FEFO allocation with conditional updates; caller owns a transaction."""
    remaining = positive(qty)
    picks = []
    today = date.today().isoformat()
    candidates = db.inventory_batches.find({
        'product_id': product_id, 'condition': 'available',
        'unverified': False, 'expires_on': {'$gte': today},
    }, session=session).sort([('expires_on', 1), ('lot', 1), ('id', 1)])
    for batch in candidates:
        available = batch['on_hand'] - batch['reserved']
        take = min(max(available, 0), remaining)
        if not take:
            continue
        result = db.inventory_batches.update_one({
            'id': batch['id'], 'reserved': batch['reserved'],
            'on_hand': batch['on_hand'], 'condition': 'available',
            'unverified': False,
        }, {'$inc': {'reserved': take}}, session=session)
        if result.matched_count != 1:
            raise InventoryProblem('Concurrent stock change; retry operation.')
        picks.append((batch, take))
        remaining -= take
        if remaining == 0:
            break
    if remaining:
        raise InventoryProblem(f'Insufficient eligible stock for {product_id}.')
    return picks


def reserve_order(order_id, actor, key):
    def run(session):
        op_id = operation(session, 'reserve-order', key, actor)
        order = db.orders.find_one({'id': order_id}, session=session)
        if not order:
            raise InventoryProblem('Order not found.', 404)
        if order.get('status') != 'Pending':
            raise InventoryProblem('Only Pending orders can be approved.')
        totals = defaultdict(int)
        for line in order.get('lines', []):
            totals[line['id']] += positive(line['qty'])
        if not totals:
            raise InventoryProblem('Order has no items.', 400)
        allocations = []
        for product_id, quantity in sorted(totals.items()):
            for batch, take in allocate(session, product_id, quantity):
                allocations.append({'id': uuid4().hex, 'order_id': order_id,
                    'batch_id': batch['id'], 'product_id': product_id,
                    'qty': take, 'status': 'active', 'operation_id': op_id})
        db.stock_reservations.insert_many(allocations, session=session)
        result = db.orders.update_one({'id': order_id, 'status': 'Pending'},
            {'$set': {'status': 'Approved', 'approved_by': actor,
                      'approved_at': now()}}, session=session)
        if result.matched_count != 1:
            raise InventoryProblem('Order changed before approval.')
        return {'order_id': order_id, 'status': 'Approved', 'reservations': [clean(a) for a in allocations]}
    return transaction(run)


def fulfill_reserved(order_id, actor, key):
    def run(session):
        op_id = operation(session, 'fulfill-order', key, actor)
        order = db.orders.find_one({'id': order_id}, session=session)
        if not order or order.get('status') != 'Approved':
            raise InventoryProblem('Only Approved orders can be fulfilled.')
        reservations = list(db.stock_reservations.find(
            {'order_id': order_id, 'status': 'active'}, session=session))
        if not reservations:
            raise InventoryProblem('No active reservations found.')
        for r in reservations:
            batch = get_batch(session, r['batch_id'])
            ensure_eligible(batch)
            result = db.inventory_batches.update_one({
                'id': batch['id'], 'on_hand': {'$gte': r['qty']},
                'reserved': {'$gte': r['qty']}, 'condition': 'available',
                'unverified': False, 'expires_on': {'$gte': date.today().isoformat()},
            }, {'$inc': {'on_hand': -r['qty'], 'reserved': -r['qty']}}, session=session)
            if result.matched_count != 1:
                raise InventoryProblem('Reserved batch stock changed.')
            db.products.update_one({'id': batch['product_id']}, {'$inc': {'quantity': -r['qty']}}, session=session)
            movement(session, batch, 'fulfill', -r['qty'],
                     batch['on_hand'], batch['on_hand'] - r['qty'], actor, order_id, op_id)
        db.stock_reservations.update_many({'order_id': order_id, 'status': 'active'},
            {'$set': {'status': 'fulfilled', 'fulfilled_at': now()}}, session=session)
        result = db.orders.update_one({'id': order_id, 'status': 'Approved'},
            {'$set': {'status': 'Fulfilled', 'fulfilled_by': actor,
                      'fulfilled_at': now()}}, session=session)
        if result.matched_count != 1:
            raise InventoryProblem('Order changed during fulfillment.')
        return {'order_id': order_id, 'status': 'Fulfilled'}
    return transaction(run)


def cancel_order(order_id, actor, key):
    def run(session):
        operation(session, 'cancel-order', key, actor)
        order = db.orders.find_one({'id': order_id}, session=session)
        if not order or order.get('status') not in ('Pending', 'Approved'):
            raise InventoryProblem('Only Pending or Approved orders may be cancelled.')
        if order['status'] == 'Approved':
            for r in db.stock_reservations.find({'order_id': order_id, 'status': 'active'}, session=session):
                result = db.inventory_batches.update_one({'id': r['batch_id'],
                    'reserved': {'$gte': r['qty']}},
                    {'$inc': {'reserved': -r['qty']}}, session=session)
                if result.matched_count != 1:
                    raise InventoryProblem('Reservation balance mismatch.')
            db.stock_reservations.update_many({'order_id': order_id, 'status': 'active'},
                {'$set': {'status': 'cancelled'}}, session=session)
        result = db.orders.update_one({'id': order_id, 'status': order['status']},
            {'$set': {'status': 'Cancelled', 'cancelled_by': actor, 'cancelled_at': now()}},
            session=session)
        if result.matched_count != 1:
            raise InventoryProblem('Order status changed.')
        return {'order_id': order_id, 'status': 'Cancelled'}
    return transaction(run)


def manual_release(product_id, qty, actor, key, reason):
    if not isinstance(reason, str) or not reason.strip():
        raise InventoryProblem('Release reason is required.', 400)
    def run(session):
        op_id = operation(session, 'manual-release', key, actor)
        details = []
        for batch, quantity in allocate(session, product_id, qty):
            result = db.inventory_batches.update_one({'id': batch['id'],
                'on_hand': {'$gte': quantity}, 'reserved': {'$gte': quantity}},
                {'$inc': {'on_hand': -quantity, 'reserved': -quantity}}, session=session)
            if result.matched_count != 1:
                raise InventoryProblem('Batch changed during release.')
            db.products.update_one({'id': product_id}, {'$inc': {'quantity': -quantity}}, session=session)
            movement(session, batch, 'manual_release', -quantity,
                batch['on_hand'], batch['on_hand'] - quantity, actor, reason, op_id)
            details.append({'batch_id': batch['id'], 'qty': quantity})
        return {'product_id': product_id, 'released': positive(qty), 'allocations': details}
    return transaction(run)


def request_adjustment(batch_id, delta, reason, actor):
    delta = signed(delta)
    if not isinstance(reason, str) or not reason.strip():
        raise InventoryProblem('Adjustment reason is required.', 400)
    batch = db.inventory_batches.find_one({'id': batch_id})
    if not batch:
        raise InventoryProblem('Batch not found.', 404)
    doc = {'id': uuid4().hex, 'batch_id': batch_id, 'delta': delta,
        'reason': reason.strip(), 'status': 'pending',
        'observed_on_hand': batch['on_hand'], 'requested_by': actor, 'requested_at': now()}
    db.inventory_adjustments.insert_one(doc)
    return clean(doc)


def decide_adjustment(adj_id, approve, actor, key):
    def run(session):
        op_id = operation(session, 'adjustment-decision', key, actor)
        doc = db.inventory_adjustments.find_one({'id': adj_id, 'status': 'pending'}, session=session)
        if not doc:
            raise InventoryProblem('Pending adjustment not found.', 404)
        if doc['requested_by'] == actor:
            raise InventoryProblem('Requester cannot approve their own adjustment.', 403)
        if approve:
            batch = get_batch(session, doc['batch_id'])
            if batch['on_hand'] != doc['observed_on_hand']:
                raise InventoryProblem('Stock changed since adjustment was requested.')
            new_balance = batch['on_hand'] + doc['delta']
            if new_balance < batch['reserved'] or new_balance < 0:
                raise InventoryProblem('Adjustment would invalidate available/reserved balances.')
            result = db.inventory_batches.update_one({'id': batch['id'],
                'on_hand': doc['observed_on_hand']}, {'$inc': {'on_hand': doc['delta']}}, session=session)
            if result.matched_count != 1:
                raise InventoryProblem('Stock changed during adjustment.')
            db.products.update_one({'id': batch['product_id']}, {'$inc': {'quantity': doc['delta']}}, session=session)
            movement(session, batch, 'adjustment', doc['delta'],
                batch['on_hand'], new_balance, actor, doc['reason'], op_id)
        db.inventory_adjustments.update_one({'id': adj_id, 'status': 'pending'},
            {'$set': {'status': 'approved' if approve else 'rejected',
                'reviewed_by': actor, 'reviewed_at': now()}}, session=session)
        return {'id': adj_id, 'status': 'approved' if approve else 'rejected'}
    return transaction(run)


def dispose(batch_id, qty, actor, key, reason):
    qty = positive(qty)
    if not isinstance(reason, str) or not reason.strip():
        raise InventoryProblem('Disposal reason is required.', 400)
    def run(session):
        op_id = operation(session, 'dispose', key, actor)
        batch = get_batch(session, batch_id)
        restricted = batch['condition'] in ('quarantine', 'damaged', 'recalled') or batch['expires_on'] < date.today().isoformat()
        if not restricted:
            raise InventoryProblem('Disposal is limited to restricted or expired batches.')
        if batch['reserved']:
            raise InventoryProblem('Release reservations before disposal.')
        result = db.inventory_batches.update_one({'id': batch_id, 'on_hand': {'$gte': qty}, 'reserved': 0},
            {'$inc': {'on_hand': -qty}}, session=session)
        if result.matched_count != 1:
            raise InventoryProblem('Insufficient physical stock for disposal.')
        db.products.update_one({'id': batch['product_id']}, {'$inc': {'quantity': -qty}}, session=session)
        movement(session, batch, 'disposal', -qty, batch['on_hand'], batch['on_hand'] - qty,
                 actor, reason, op_id)
        return {'batch_id': batch_id, 'disposed': qty}
    return transaction(run)


def receive_return(order_id, product_id, lot, expires_on, qty, actor, key, reason):
    """Receive a fulfilled-order return into quarantine, never automatically saleable."""
    qty = positive(qty)
    expires_on = expiry(expires_on)
    if not isinstance(lot, str) or not lot.strip():
        raise InventoryProblem('Returned stock requires a lot identifier.', 400)
    if not isinstance(reason, str) or not reason.strip():
        raise InventoryProblem('Return reason is required.', 400)

    def run(session):
        op_id = operation(session, 'customer-return', key, actor)
        order = db.orders.find_one({'id': order_id, 'status': 'Fulfilled'}, session=session)
        if not order:
            raise InventoryProblem('Only fulfilled orders can receive returns.')
        delivered = sum(positive(line['qty']) for line in order.get('lines', [])
                        if line.get('id') == product_id)
        previous = sum(abs(m['qty']) for m in db.stock_movements.find({
            'product_id': product_id, 'action': 'return', 'reference': order_id,
        }, {'qty': 1}, session=session))
        if not delivered or qty > delivered - previous:
            raise InventoryProblem('Return would exceed fulfilled order quantity.')
        batch = db.inventory_batches.find_one_and_update({
            'product_id': product_id, 'lot': lot.strip(), 'expires_on': expires_on,
            'condition': 'quarantine', 'unverified': False},
            {'$inc': {'on_hand': qty}, '$setOnInsert': {'id': uuid4().hex,
                'reserved': 0, 'created_at': now(), 'unverified': False}},
            upsert=True, return_document=ReturnDocument.AFTER, session=session)
        db.products.update_one({'id': product_id}, {'$inc': {'quantity': qty}}, session=session)
        movement(session, batch, 'return', qty, batch['on_hand'] - qty,
                 batch['on_hand'], actor, order_id, op_id)
        return {'order_id': order_id, 'batch_id': batch['id'], 'received_quarantine': qty}
    return transaction(run)


def restrict_batch(batch_id, condition, actor, key, reason):
    if condition not in ('quarantine', 'damaged', 'recalled'):
        raise InventoryProblem('Can only restrict batches to quarantine, damaged, or recalled.', 400)
    if not isinstance(reason, str) or not reason.strip():
        raise InventoryProblem('Reason is required.', 400)
    def run(session):
        op_id = operation(session, 'restrict-batch', key, actor)
        batch = get_batch(session, batch_id)
        if batch['reserved'] > 0:
            raise InventoryProblem('Cancel or reallocate reservations before restricting a batch.')
        result = db.inventory_batches.update_one({'id': batch_id, 'reserved': 0,
            'condition': batch['condition']}, {'$set': {'condition': condition}}, session=session)
        if result.matched_count != 1:
            raise InventoryProblem('Batch changed during restriction.')
        movement(session, batch, 'condition_' + condition, 0,
                 batch['on_hand'], batch['on_hand'], actor, reason, op_id)
        return {'batch_id': batch_id, 'condition': condition}
    return transaction(run)


def receive_delivery(lines, reference, actor, key):
    """Receive a delivery of 1..50 batch lines in a single MongoDB transaction.

    All lines are validated before mutation. The shared operation key enforces
    idempotency. Any failure rolls back all batches and movement records.
    """
    if not isinstance(lines, list) or not 1 <= len(lines) <= 50:
        raise InventoryProblem('Delivery requires 1 to 50 lines.', 400)
    if not isinstance(reference, str) or not reference.strip() or len(reference.strip()) > 150:
        raise InventoryProblem('Delivery reference is required (max 150 characters).', 400)
    if not isinstance(key, str) or not 8 <= len(key) <= 128:
        raise InventoryProblem('Idempotency-Key header must contain 8–128 characters.', 400)
    normalized = []
    for index, item in enumerate(lines, start=1):
        if not isinstance(item, dict):
            raise InventoryProblem(f'Line {index}: invalid object.', 400)
        pid = item.get('product_id')
        lot = item.get('lot')
        condition = item.get('condition', 'available')
        if not isinstance(pid, str) or not pid.strip():
            raise InventoryProblem(f'Line {index}: product required.', 400)
        if not isinstance(lot, str) or not lot.strip() or len(lot.strip()) > 100:
            raise InventoryProblem(f'Line {index}: lot required (max 100 characters).', 400)
        if condition not in ('available', 'quarantine'):
            raise InventoryProblem(f'Line {index}: invalid condition.', 400)
        try:
            qty = positive(item.get('qty'))
            exp = expiry(item.get('expires_on'))
        except InventoryProblem as exc:
            raise InventoryProblem(f'Line {index}: {exc}', exc.status) from exc
        if condition == 'available' and exp < date.today().isoformat():
            raise InventoryProblem(f'Line {index}: expired stock must be quarantined.', 409)
        normalized.append((pid.strip(), lot.strip(), exp, qty, condition))

    def run(session):
        op_id = operation(session, 'receive_delivery', key, actor)
        product_ids = set(p for p, *_ in normalized)
        found = {p['id'] for p in db.products.find(
            {'id': {'$in': list(product_ids)}}, {'id': 1}, session=session)}
        missing = product_ids - found
        if missing:
            raise InventoryProblem('Product not found: ' + ', '.join(sorted(missing)), 404)
        received = []
        for pid, lot, exp, qty, condition in normalized:
            batch = db.inventory_batches.find_one_and_update(
                {'product_id': pid, 'lot': lot, 'expires_on': exp,
                 'condition': condition, 'unverified': False},
                {'$inc': {'on_hand': qty}, '$setOnInsert': {'id': uuid4().hex,
                    'reserved': 0, 'created_at': now(), 'unverified': False}},
                upsert=True, return_document=ReturnDocument.AFTER, session=session)
            db.products.update_one({'id': pid}, {'$inc': {'quantity': qty}}, session=session)
            movement(session, batch, 'receive', qty, batch['on_hand'] - qty,
                     batch['on_hand'], actor, reference.strip(), op_id)
            received.append({'product_id': pid, 'batch_id': batch['id'],
                             'lot': lot, 'qty': qty, 'expires_on': exp})
        return {'operation_id': op_id, 'reference': reference.strip(),
                'lines_received': len(received), 'units_received': sum(x['qty'] for x in received),
                'items': received}
    return transaction(run)
