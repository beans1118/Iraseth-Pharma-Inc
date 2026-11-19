"""Reconstruct reviewed brochure products in a NEW, explicitly named local DB.

Read-only by default. Does not load .env or start Flask. Never repairs an existing
database. Product validation/persistence use the existing brochure/product services.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
DEFAULT_DATABASE = 'iraseth'
DEFAULT_URI = 'mongodb://127.0.0.1:27017/?replicaSet=rs0'


def validate_target(database, uri):
    if (database not in (DEFAULT_DATABASE, 'iraseth_dev')
            and not re.fullmatch(r'iraseth_local_[a-z][a-z0-9_]{0,39}', database or '')) or re.search(r'prod|staging', database or '', re.I):
        raise ValueError('Use iraseth, or an explicit iraseth_local_<purpose> override. iraseth_dev is read-only; test/production/staging targets are refused.')
    try:
        parsed = urlsplit(uri)
        options = parse_qs(parsed.query, keep_blank_values=True)
        valid = (parsed.scheme == 'mongodb' and parsed.hostname in ('127.0.0.1', 'localhost', '::1')
                 and parsed.username is None and parsed.password is None and ',' not in parsed.netloc
                 and parsed.path in ('', '/') and 0 < (parsed.port or 27017) < 65536
                 and options.get('replicaSet') == ['rs0']
                 and set(options) <= {'replicaSet'})
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Use one credential-free loopback MongoDB endpoint with /?replicaSet=rs0; no remote discovery, credentials, URI database or other options.')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build_documents():
    from modules.brochure.service import load_manifest, FOLDER, provisional_selections, digest
    from modules.brochure.assessment import assess
    from modules.brochure.routes import selected_documents
    from modules.product_metadata import metadata

    manifest, _ = load_manifest()
    review = read_json(FOLDER / 'pdf-product-image-review.json')
    reports = [read_json(ROOT / 'docs/pdf-products' / name) for name in
               ('dev-first-batch-dry-run.json', 'dev-next-batch-dry-run.json')]
    reports += read_json(ROOT / 'docs/pdf-products/remaining-114-dry-run.json')['batches']
    documents = []
    selected = []
    for report in reports:
        keys = report['candidate_ids']
        selections = provisional_selections(manifest, keys, review, report.get('duplicate_reviews', {}))
        documents += selected_documents(selections, manifest, documents)
        selected += keys
    expected = {c['candidate_id'] for c in manifest['candidates'] if assess(c)['source_ready']}
    if len(selected) != 124 or len(set(selected)) != 124 or set(selected) != expected:
        raise ValueError('Reviewed selections no longer cover exactly the 124 approved source-clear products.')

    # Replay only the three completed, reviewed image mappings, never ambiguous
    # family photos or the unapproved HBsAg crop. No database export is read.
    image_plan = read_json(ROOT / 'docs/product-images/image-audit-and-plan.json')
    completed = read_json(ROOT / 'docs/product-images/image-update-results.json')
    if (completed['status'] != 'complete' or completed['updated_count'] != 3
            or completed['source_sha256'] != manifest['source_sha256']
            or image_plan['source_sha256'] != manifest['source_sha256']):
        raise ValueError('Completed image review does not match the source.')
    by_id = {doc['id']: doc for doc in documents}
    for update in image_plan['proposed_updates']:
        doc = by_id[update['id']]
        files = [item['candidate'] for item in update['files']]
        if doc['name'] != update['name'] or not any(r['id'] == doc['id'] and r['files'] == files for r in completed['results']):
            raise ValueError('Image mapping does not match completed review.')
        gallery = []
        for item in update['files']:
            path = (ROOT / item['candidate']).resolve()
            if not path.is_relative_to((ROOT / 'docs').resolve()):
                raise ValueError('Image path leaves source documentation.')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != item['candidate_sha256']:
                raise ValueError('Reviewed image hash mismatch.')
            gallery.append('data:image/webp;base64,' + base64.b64encode(raw).decode())
        doc.update(metadata({'images': gallery, 'image': gallery[0]}))
    # Exclude timestamps from the reproducible content fingerprint.
    content_hash = digest([{k: v for k, v in d.items() if k != 'created_at'} for d in documents])
    return documents, content_hash


def status(database):
    return {name: database[name].count_documents({}) for name in sorted(database.list_collection_names())}


def run(database, documents, content_hash, apply=False):
    from config import Config
    from routes.products import insert_product_document
    from modules.inventory.readiness import check_ready
    validate_target(database.name, Config.MONGO_URI)
    hello = database.client.admin.command('hello')
    # Checking every advertised member prevents loopback seed discovery of a
    # remote replica set; no directConnection bypass of transaction safeguards.
    members = hello.get('hosts', [])
    if hello.get('setName') != 'rs0' or not hello.get('isWritablePrimary') or not members or any(
            urlsplit('mongodb://' + host).hostname not in ('127.0.0.1', 'localhost', '::1') for host in members):
        raise ValueError('MongoDB must be a writable local-only rs0 replica set. No automatic reconfiguration is performed.')
    if len(documents) != 124 or len({d['id'] for d in documents}) != 124:
        raise ValueError('Only the complete reviewed 124-product reconstruction is permitted.')
    counts = status(database)
    report = {'database': database.name, 'existing_products': counts.get('products', 0),
              'collection_counts': counts, 'source_products': len(documents), 'content_sha256': content_hash,
              'image_products': sum(bool(d['images']) for d in documents),
              'unavailable_original_ids': ['MED-001', 'MED-002', 'SMP-001']}
    if database.name == 'iraseth_dev':
        return {**report, 'status': 'legacy-read-only', 'created': 0,
                'message': 'Existing iraseth_dev is supported for reporting only, including --apply. No products, indexes, readiness or audit records changed. Use iraseth for new setup.'}
    if any(counts.values()):
        marker = database.system_metadata.find_one({'_id': 'local_catalog_setup'})
        report.update(status='already-initialized' if marker and marker.get('content_sha256') == content_hash else 'existing-data-skipped',
                      created=0, message='Existing data preserved. No inserts, updates, indexes or readiness changes. Use another NEW local database for reconstruction.')
        return report
    with database.client.start_session() as session:
        with session.start_transaction():
            database.products.find_one({}, session=session)
    if not apply:
        return {**report, 'status': 'dry-run', 'created': 0,
                'message': 'Would atomically insert 124 provisional products, catalog audit events and empty-stock batch readiness. No database writes or indexes.'}

    # Index/collection creation is allowed only after explicit apply and an empty
    # database check. A unique marker and product keys serialize competing setup.
    database.products.create_index('id', unique=True)
    for field in ('_sku_key', '_brochure_identity'):
        database.products.create_index(field, unique=True, partialFilterExpression={field: {'$type': 'string'}})
    for name in ('catalog_events', 'system_metadata'):
        if name not in database.list_collection_names():
            database.create_collection(name)
    names = database.list_collection_names()

    def create(session):
        if any(database[name].find_one({}, session=session) is not None for name in names):
            raise ValueError('Data appeared during setup. Transaction aborted; no products overwritten.')
        now = datetime.now(timezone.utc).isoformat()
        database.system_metadata.insert_one({'_id': 'local_catalog_setup', 'content_sha256': content_hash,
                                             'count': 124, 'at': now}, session=session)
        for document in documents:
            doc = dict(document)
            insert_product_document(doc, session=session)
            database.catalog_events.insert_one({'id': uuid4().hex, 'product_id': doc['id'],
                'action': 'local_catalog_setup', 'actor_email': 'local-setup@example.invalid',
                'source': doc['brochure_source'], 'content_sha256': content_hash, 'at': now}, session=session)
        database.system_metadata.insert_one({'_id': 'batch_mode_ready', 'approved': True,
            'reason': 'New local catalog only: all quantities zero; no inventory or migration.', 'at': now}, session=session)
    with database.client.start_session() as session:
        session.with_transaction(create)
    check_ready(database, require_marker=True)
    return {**report, 'status': 'initialized', 'created': 124,
            'message': '124 provisional products and reviewed galleries created. No users, stock, orders, customer records or approved prices copied.'}


def configure(database, uri):
    validate_target(database, uri)
    # Explicit CLI selection takes precedence over inherited/local environment.
    # No .env is read and no Flask app/index initialization occurs on import.
    os.environ.update(APP_ENV='development', DEPLOYMENT_ENVIRONMENT='', MONGO_DB_NAME=database,
                      MONGO_URI=uri, BATCH_MODE='true', MONGO_SERVER_SELECTION_TIMEOUT_MS='3000')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=DEFAULT_DATABASE)
    parser.add_argument('--uri', default=DEFAULT_URI)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--confirm-database')
    args = parser.parse_args()
    try:
        configure(args.database, args.uri)
        if args.apply and args.confirm_database != args.database:
            raise ValueError('--apply requires --confirm-database matching the selected database.')
        documents, content_hash = build_documents()
        from extensions import db
        if db.name != args.database:
            raise ValueError('Loaded database differs from explicit selection.')
        print(json.dumps(run(db, documents, content_hash, args.apply), indent=2))
        return 0
    except ValueError as exc:
        print('Local setup blocked: ' + str(exc), file=sys.stderr)
    except Exception as exc:
        # Mongo errors can contain URI credentials. Never print raw exceptions.
        print('Local setup failed (' + type(exc).__name__ + '). Check local MongoDB/rs0, source files and dependencies. No target fallback or overwrite.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
