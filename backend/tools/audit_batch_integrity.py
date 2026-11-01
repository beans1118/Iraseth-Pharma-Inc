"""Read-only inventory consistency report. NO mutation. Explicit DB selection only.

Usage: python tools/audit_batch_integrity.py --database iraseth_test
       python tools/audit_batch_integrity.py --database iraseth_dev
Exit 0 = checks passed; 2 = inconsistency found; 1 = connection/usage error.
"""
import argparse
from collections import defaultdict
from datetime import date
from pymongo import MongoClient


def audit(db):
    failures = []
    products = {p['id']: p for p in db.products.find({}, {'id': 1, 'quantity': 1})}
    batches = list(db.inventory_batches.find({}, {'id': 1, 'product_id': 1, 'on_hand': 1,
                          'reserved': 1, 'condition': 1, 'expires_on': 1, 'unverified': 1}))
    physical = defaultdict(int)
    by_id = {}
    for b in batches:
        bid = b.get('id')
        if bid in by_id:
            failures.append(f'Duplicate batch id: {bid}')
        by_id[bid] = b
        pid = b.get('product_id')
        on_hand, reserved = b.get('on_hand'), b.get('reserved')
        if type(on_hand) is not int or type(reserved) is not int or not (0 <= reserved <= on_hand):
            failures.append(f'Invalid balance in batch {bid}')
            continue
        physical[pid] += on_hand
        if pid not in products:
            failures.append(f'Orphan batch {bid}: missing product {pid}')
        if b.get('unverified'):
            failures.append(f'Unverified batch {bid}')
        if reserved and (b.get('condition') != 'available' or b.get('expires_on', '') < date.today().isoformat()):
            failures.append(f'Restricted/expired batch has reservations: {bid}')
    for pid, p in products.items():
        if type(p.get('quantity')) is not int or p['quantity'] < 0 or p['quantity'] != physical[pid]:
            failures.append(f'Quantity mismatch: {pid}, product={p.get("quantity")}, batch_sum={physical[pid]}')
    active = defaultdict(int)
    for r in db.stock_reservations.find({'status': 'active'}, {'id': 1, 'batch_id': 1, 'qty': 1, 'order_id': 1}):
        batch = by_id.get(r.get('batch_id'))
        if batch is None:
            failures.append(f'Orphan active reservation {r.get("id")}')
            continue
        if type(r.get('qty')) is not int or r['qty'] <= 0:
            failures.append(f'Invalid active reservation quantity {r.get("id")}')
            continue
        active[r['batch_id']] += r['qty']
        order = db.orders.find_one({'id': r.get('order_id')}, {'status': 1})
        if not order or order.get('status') != 'Approved':
            failures.append(f'Active reservation for non-Approved/missing order: {r.get("id")}')
    for bid, batch in by_id.items():
        if batch.get('reserved') != active[bid]:
            failures.append(f'Reserved mismatch: {bid}, batch={batch.get("reserved")}, active={active[bid]}')
    return len(products), len(batches), sum(active.values()), failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True, choices=['iraseth_test', 'iraseth_dev'])
    args = parser.parse_args()
    client = MongoClient('mongodb://127.0.0.1:27017/?replicaSet=rs0', serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    count_products, count_batches, reserved, failures = audit(client[args.database])
    print(f'Database={args.database}; products={count_products}; batches={count_batches}; active_reserved_units={reserved}')
    for issue in failures:
        print('FAIL:', issue)
    print('PASS: no inconsistencies found' if not failures else f'FAIL: {len(failures)} issue(s)')
    raise SystemExit(2 if failures else 0)


if __name__ == '__main__':
    main()
