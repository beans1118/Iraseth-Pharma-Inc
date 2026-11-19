"""Setup safety coverage, separate from legacy tests/conftest.py.

Run with IRASETH_LOCAL_VERIFY_URI=mongodb://127.0.0.1:27028/?replicaSet=rs0
against a disposable rs0 instance. Port 27017 is deliberately refused here.
"""
import os
from pathlib import Path
import sys
from uuid import uuid4

from bson.json_util import dumps
import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / 'tools'))
from setup_local_catalog import validate_target, configure, build_documents, run
from configure_local import configure_files


@pytest.mark.parametrize('name,uri', [
    ('iraseth_pharma', 'mongodb://127.0.0.1:27028/?replicaSet=rs0'),
    ('iraseth_test', 'mongodb://127.0.0.1:27028/?replicaSet=rs0'),
    ('iraseth_local_production', 'mongodb://127.0.0.1:27028/?replicaSet=rs0'),
    ('iraseth_local_staging', 'mongodb://127.0.0.1:27028/?replicaSet=rs0'),
    ('iraseth', 'mongodb+srv://remote.invalid/'),
    ('iraseth', 'mongodb://remote.invalid/?replicaSet=rs0'),
    ('iraseth', 'mongodb://127.0.0.1,remote.invalid/?replicaSet=rs0'),
    ('iraseth', 'mongodb://user:secret@127.0.0.1/?replicaSet=rs0'),
    ('iraseth', 'mongodb://127.0.0.1/iraseth_dev?replicaSet=rs0'),
    ('iraseth', 'mongodb://127.0.0.1/?replicaSet=rs0&directConnection=true'),
    ('iraseth', 'mongodb://127.0.0.1/?replicaSet=other'),
])
def test_unsafe_targets_refused(name, uri):
    with pytest.raises(ValueError):
        validate_target(name, uri)


@pytest.mark.parametrize('database', ['iraseth', 'iraseth_dev', 'iraseth_local_sandbox'])
def test_default_legacy_and_explicit_sandbox_are_supported(database):
    validate_target(database, 'mongodb://127.0.0.1:27028/?replicaSet=rs0')


def test_environment_files_are_exclusive_and_target_mismatch_is_refused(tmp_path):
    for directory in ('backend', 'frontend', 'storefront-next'):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / '.env.example').write_bytes((BACKEND.parent / directory / '.env.example').read_bytes())
    uri = 'mongodb://127.0.0.1:27028/?replicaSet=rs0'
    configure_files(tmp_path, 'iraseth', uri, check=True)
    assert not (tmp_path / 'backend/.env').exists()
    configure_files(tmp_path, 'iraseth', uri)
    paths = [tmp_path / p for p in ('backend/.env', 'frontend/.env', 'storefront-next/.env.local')]
    before = [p.read_bytes() for p in paths]
    configure_files(tmp_path, 'iraseth', uri)
    assert before == [p.read_bytes() for p in paths]
    assert b'BATCH_MODE=true' in before[0]
    with pytest.raises(ValueError, match='preserved'):
        configure_files(tmp_path, 'iraseth_local_other', uri)
    assert before == [p.read_bytes() for p in paths]


def test_existing_next_environment_is_not_shadowed(tmp_path, monkeypatch):
    for key in ('APP_ENV', 'DEPLOYMENT_ENVIRONMENT', 'MONGO_DB_NAME', 'MONGO_URI'):
        monkeypatch.delenv(key, raising=False)
    for directory in ('backend', 'frontend', 'storefront-next'):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / '.env.example').write_bytes((BACKEND.parent / directory / '.env.example').read_bytes())
    existing = tmp_path / 'storefront-next/.env'
    existing.write_text('CATALOG_API_BASE_URL=http://127.0.0.1:5999\n')
    before = existing.read_bytes()
    configure_files(tmp_path, 'iraseth', 'mongodb://127.0.0.1:27028/?replicaSet=rs0')
    assert existing.read_bytes() == before
    assert not (tmp_path / 'storefront-next/.env.local').exists()


def test_shell_target_override_is_refused_before_creating_files(tmp_path, monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    with pytest.raises(ValueError, match='Shell variable APP_ENV'):
        configure_files(tmp_path, 'iraseth', 'mongodb://127.0.0.1:27028/?replicaSet=rs0')
    assert list(tmp_path.iterdir()) == []


@pytest.fixture(scope='module')
def source():
    uri = os.environ.get('IRASETH_LOCAL_VERIFY_URI')
    if uri != 'mongodb://127.0.0.1:27028/?replicaSet=rs0':
        pytest.fail('Explicit disposable local rs0 at port 27028 required; original MongoDB is never used.')
    configure('iraseth_local_verify_' + uuid4().hex[:12], uri)
    return build_documents()


@pytest.fixture
def target(source, monkeypatch):
    from extensions import db
    import routes.products
    database = db.client['iraseth_local_verify_' + uuid4().hex[:12]]
    assert not database.list_collection_names()
    monkeypatch.setattr(routes.products, 'db', database)
    return database


def fingerprint(db):
    return dumps({name: {'records': list(db[name].find().sort('_id', 1)), 'indexes': list(db[name].list_indexes())}
                  for name in sorted(db.list_collection_names())}, sort_keys=True)


def test_empty_mongodb_is_a_successful_public_catalog_response(target, monkeypatch):
    from flask import Flask
    import modules.public_catalog.routes as public
    monkeypatch.setattr(public, 'db', target)
    app = Flask(__name__)
    app.register_blueprint(public.bp)
    before = fingerprint(target)
    response = app.test_client().get('/api/public/products')
    assert response.status_code == 200
    assert response.get_json() == {'products': [], 'total': 0, 'page': 1, 'pageSize': 100, 'hasMore': False}
    assert fingerprint(target) == before


def test_legacy_database_is_report_only_even_when_empty_or_apply_is_requested(source, target):
    legacy = target.client['iraseth_dev']
    before = fingerprint(legacy)
    result = run(legacy, *source, apply=True)
    assert result['status'] == 'legacy-read-only' and result['created'] == 0
    assert fingerprint(legacy) == before


def test_disposable_regression_configuration_ignores_private_environment(tmp_path, monkeypatch):
    from utils.test_configuration import local_test_settings
    (tmp_path / '.env.test.example').write_bytes((BACKEND / '.env.test.example').read_bytes())
    (tmp_path / '.env.test').write_text('APP_ENV=production\nMONGO_DB_NAME=iraseth_dev\n')
    monkeypatch.setenv('IRASETH_TEST_MONGO_PORT', '27028')
    settings, uri, port = local_test_settings(tmp_path)
    assert settings['APP_ENV'] == 'testing' and settings['MONGO_DB_NAME'] == 'iraseth_test'
    assert uri == 'mongodb://127.0.0.1:27028/?replicaSet=rs0' and port == 27028


@pytest.mark.parametrize('port', ['27029', 'remote.invalid:27017', '0'])
def test_unapproved_regression_targets_are_refused(tmp_path, monkeypatch, port):
    from utils.test_configuration import local_test_settings
    monkeypatch.setenv('IRASETH_TEST_MONGO_PORT', port)
    with pytest.raises(ValueError, match='disposable test port'):
        local_test_settings(tmp_path)


def test_reconstruction_dry_run_atomic_apply_repeat_and_api_identity(source, target, monkeypatch):
    docs, digest = source
    assert len(docs) == 124
    assert sum(bool(d['images']) for d in docs) == 11
    assert sum(len(d['images']) for d in docs) == 12
    before = fingerprint(target)
    assert run(target, docs, digest)['status'] == 'dry-run'
    assert fingerprint(target) == before
    assert run(target, docs, digest, apply=True)['created'] == 124
    assert target.catalog_events.count_documents({}) == 124
    for doc in target.products.find():
        assert doc['identity_status'] == 'provisional' and doc['sku'] == ''
        assert doc['quantity'] == doc['baseline_qty'] == 0
        assert doc['price'] is None and doc['storefront_price'] is None
    before = fingerprint(target)
    assert run(target, docs, digest, apply=True)['status'] == 'already-initialized'
    assert fingerprint(target) == before

    from flask import Flask
    import modules.public_catalog.routes as public
    import routes.products as products
    monkeypatch.setattr(public, 'db', target)
    app = Flask(__name__)
    app.register_blueprint(public.bp)
    # Call the ordinary employee handler without authentication only in this
    # isolated test; browser verification separately exercises a real login.
    public_ids = []
    client = app.test_client()
    for page, count in ((1, 100), (2, 24)):
        response = client.get(f'/api/public/products?page={page}&limit=100')
        assert response.status_code == 200
        body = response.get_json()
        assert body['total'] == 124 and len(body['products']) == count
        assert body['hasMore'] == (page == 1)
        assert all(not p['inStock'] and p['publicPrice'] is None for p in body['products'])
        public_ids += [p['id'] for p in body['products']]
    with app.test_request_context('/api/products?page=1&limit=200'):
        staff = products.list_products.__wrapped__()
        assert staff.headers['X-Total-Count'] == '124'
        assert {p['id'] for p in staff.get_json()} == set(public_ids)
    with app.test_request_context('/api/products?q=Microfusion&category=Infusion%20and%20Transfusion'):
        assert any(p['name'] == 'Microfusion Set' for p in products.list_products.__wrapped__().get_json())


@pytest.mark.parametrize('collection', ['products', 'orders', 'inventory_batches', 'users', 'catalog_events'])
def test_any_preexisting_data_is_preserved_without_index_writes(source, target, collection):
    docs, digest = source
    target[collection].insert_one({'sentinel': uuid4().hex})
    before = fingerprint(target)
    result = run(target, docs, digest, apply=True)
    assert result['status'] == 'existing-data-skipped' and result['created'] == 0
    assert fingerprint(target) == before


def test_failure_rolls_back_entire_catalog_and_readiness(source, target, monkeypatch):
    import routes.products
    original = routes.products.insert_product_document
    count = 0
    def fail(doc, session=None):
        nonlocal count
        count += 1
        if count == 3:
            raise ValueError('Injected failure')
        original(doc, session=session)
    monkeypatch.setattr(routes.products, 'insert_product_document', fail)
    with pytest.raises(ValueError, match='Injected'):
        run(target, *source, apply=True)
    assert target.products.count_documents({}) == 0
    assert target.catalog_events.count_documents({}) == 0
    assert target.system_metadata.count_documents({}) == 0
