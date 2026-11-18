"""Read-only by default. Explicitly initialize an EMPTY Atlas staging database.

Creates genuine configured staff accounts and an empty-inventory readiness
marker only. Never copies local data, seeds products, imports brochures, changes
stock, or modifies existing accounts. Do not use seed.py for this operation.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils.deployment import validate_staging_target

ROLES = {'superadmin', 'admin', 'subadmin'}
TRANSIENT_COLLECTIONS = {'rate_limits', 'support_rate_limits'}


def validate_accounts(accounts):
    if len(accounts) != 3 or {a.get('role') for a in accounts} != ROLES:
        raise ValueError('Configure exactly one genuine staff account for each role.')
    emails = set()
    for account in accounts:
        email = account.get('email', '').strip().lower()
        password = account.get('password', '')
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or email in emails or not account.get('name', '').strip():
            raise ValueError('Staff names and distinct genuine email addresses are required.')
        if not 12 <= len(password.encode('utf-8')) <= 72 or password.lower().startswith(('change-me', 'replace_', 'your_')):
            raise ValueError('Use genuine staff passwords of 12–72 UTF-8 bytes, never template values.')
        emails.add(email)
    if len({a['password'] for a in accounts}) != 3:
        raise ValueError('Each staging staff account needs its own password.')


def assert_empty(database, names, session=None):
    for name in names:
        if name not in TRANSIENT_COLLECTIONS and database[name].count_documents({}, limit=1, session=session):
            raise ValueError('Staging already contains business/account records. Nothing may be initialized or overwritten.')


def initialize(database, accounts, apply=False):
    if database.name != 'iraseth_staging':
        raise ValueError('Initialization is restricted to iraseth_staging.')
    validate_accounts(accounts)
    names = sorted(set(database.list_collection_names()) | {'users', 'system_metadata', 'products', 'inventory_batches'})
    assert_empty(database, names)
    hello = database.client.admin.command('hello')
    if not hello.get('setName') or hello.get('logicalSessionTimeoutMinutes') is None:
        raise ValueError('Atlas must expose a replica set with sessions/transactions.')
    # A read-only transaction validates session/transaction access without any
    # insert-and-rollback probe or catalog/inventory writes.
    with database.client.start_session() as session:
        with session.start_transaction():
            assert_empty(database, names, session)
    if not apply:
        return 'Read-only checks passed. No indexes, accounts or readiness marker written.'

    import bcrypt
    documents = [{'email':a['email'].strip().lower(), 'name':a['name'].strip(), 'role':a['role'],
                  'password_hash':bcrypt.hashpw(a['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')}
                 for a in accounts]
    # All schema writes are behind explicit --apply, outside the transaction.
    for name in ('users', 'system_metadata'):
        if name not in database.list_collection_names():
            database.create_collection(name)
    database.users.create_index('email', unique=True)
    from modules.inventory.readiness import check_ready
    def write(session):
        assert_empty(database, names, session)
        check_ready(database, require_marker=False)
        database.users.insert_many(documents, ordered=True, session=session)
        database.system_metadata.insert_one({'_id':'batch_mode_ready', 'approved':True,
            'approved_at':datetime.now(timezone.utc).isoformat(), 'scope':'empty Atlas staging initialization'}, session=session)
    with database.client.start_session() as session:
        session.with_transaction(write)
    return 'Created three staging staff accounts and empty-inventory readiness approval. No product or stock records created.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm-database', default='')
    args = parser.parse_args()
    if args.apply and args.confirm_database != 'iraseth_staging':
        parser.error('--apply also requires --confirm-database iraseth_staging')
    try:
        from config import Config
        validate_staging_target(Config.APP_ENV, Config.MONGO_DB_NAME, Config.MONGO_URI)
        if Config.DEPLOYMENT_ENVIRONMENT != 'staging':
            raise ValueError('DEPLOYMENT_ENVIRONMENT must explicitly be staging.')
        Config.validate_production()
        validate_accounts(Config.SEED_USERS)
        from pymongo import MongoClient
        with MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000) as client:
            print(initialize(client['iraseth_staging'], Config.SEED_USERS, args.apply))
        return 0
    except ValueError as exc:
        print('Staging initialization refused: '+str(exc), file=sys.stderr)
    except Exception as exc:
        # Driver exception strings may contain connection information.
        print('Staging initialization failed ('+type(exc).__name__+'). Check Atlas access and settings; no automatic retry or target switch.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
