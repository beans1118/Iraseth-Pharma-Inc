"""Explicit, guarded readiness approval for an isolated local development DB.

Requires manual batch reconciliation beforehand and never alters stock quantities.
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.inventory.readiness import check_ready


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True, choices=('iraseth_test', 'iraseth_dev'))
    parser.add_argument('--mark-ready', action='store_true')
    args = parser.parse_args()
    db = MongoClient('mongodb://127.0.0.1:27017/?replicaSet=rs0', serverSelectionTimeoutMS=5000)[args.database]
    check_ready(db, require_marker=False)
    print('All product quantities reconcile and no unverified/restricted reservations exist.')
    if args.mark_ready:
        if os.getenv('APPROVE_BATCH_MODE') != 'YES_LOCAL_ONLY':
            parser.error('Set APPROVE_BATCH_MODE=YES_LOCAL_ONLY to mark ready.')
        db.system_metadata.update_one({'_id': 'batch_mode_ready'},
            {'$set': {'approved': True, 'approved_at': datetime.now(timezone.utc).isoformat()}}, upsert=True)
        print('Batch mode readiness marker written to', args.database)
    else:
        print('Read-only verification; nothing changed.')

if __name__ == '__main__':
    main()
