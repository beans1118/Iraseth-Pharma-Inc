"""Non-destructive legacy inventory inspection/import.

Usage (from backend directory):
    python migrations/legacy_inventory.py --database iraseth_test
    python migrations/legacy_inventory.py --database iraseth_test --apply

ONLY on locally isolated disposable databases. Never run against real stock.
Creates quarantined, unverified batches; it does not certify lot numbers or expiry.
No automatic migration takes place during app startup.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pymongo import MongoClient
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True, choices=('iraseth_test', 'iraseth_dev'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    # Restrict to an explicit local database. Do not trust .env defaults.
    uri = 'mongodb://127.0.0.1:27017/?replicaSet=rs0'
    if args.apply and os.getenv('ALLOW_LEGACY_IMPORT') != 'I_ACCEPT_QUARANTINE_ONLY':
        parser.error('Set ALLOW_LEGACY_IMPORT=I_ACCEPT_QUARANTINE_ONLY before --apply')
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    database = client[args.database]
    products = list(database.products.find({}, {'id': 1, 'quantity': 1, '_id': 0}))
    errors = []
    candidates = []
    for product in products:
        qty = product.get('quantity', 0)
        if type(qty) is not int or qty < 0:
            errors.append(f"Invalid quantity for {product.get('id')}")
            continue
        if not qty:
            continue
        pid = product['id']
        if database.inventory_batches.count_documents({'product_id': pid}) > 0:
            errors.append(f'{pid}: batch records already exist; refusing to import over them')
            continue
        candidates.append((pid, qty))
    print(f'Database={args.database}, products={len(products)}, candidates={len(candidates)}, errors={len(errors)}')
    for item in errors:
        print('BLOCKER:', item)
    for pid, qty in candidates:
        print('QUARANTINE ONLY:', pid, 'quantity:', qty)
    if errors:
        raise SystemExit(2)
    if not args.apply:
        print('DRY RUN only; no documents created. --apply requires explicit confirmation environment variable.')
        return
    for pid, qty in candidates:
        with client.start_session() as session:
            def write(s):
                if database.inventory_batches.count_documents({'product_id': pid}, session=s):
                    raise RuntimeError('Concurrent import / existing batch: ' + pid)
                database.inventory_batches.insert_one({
                    'id': uuid4().hex, 'product_id': pid, 'lot': 'LEGACY-UNVERIFIED',
                    'expires_on': '1900-01-01', 'on_hand': qty, 'reserved': 0,
                    'condition': 'quarantine', 'unverified': True,
                    'imported_legacy': True,
                }, session=s)
            session.with_transaction(write)
    print('Imported into quarantine. Do NOT enable batch mode until real lots are reconciled.')


if __name__ == '__main__':
    main()
