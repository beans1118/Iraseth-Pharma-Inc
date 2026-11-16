"""Actual brochure -> staff dry run/approval -> Mongo -> public catalog.

Every write uses conftest's iraseth_test guard. QA identifiers and QA_TEST_UNIT
are disposable fixtures, never proposed inventory SKUs or approved sale units.
No source record is marked staff-approved by these tests.
"""
import base64
import hashlib
from uuid import uuid4

from bson.json_util import dumps
import pytest

from config import Config
from modules.brochure.assessment import assess
from modules.brochure.service import FOLDER, classify, load_manifest
from modules.product_metadata import valid_image


STOCK_COLLECTIONS = ('inventory_batches','inventory_logs','stock_movements',
    'stock_reservations','inventory_operations','inventory_adjustments','orders','invoices','invoice_events')


def fingerprint(collection, query=None):
    return hashlib.sha256(dumps(list(collection.find(query or {}).sort('_id',1)),sort_keys=True).encode()).hexdigest()


@pytest.fixture
def actual_import(client, auth, test_db, monkeypatch):
    assert test_db.name == 'iraseth_test'
    monkeypatch.setattr(Config, 'BATCH_MODE', True)
    manifest,_ = load_manifest()
    candidates = [c for c in manifest['candidates'] if assess(c)['source_ready']]
    prefix = 'PYTEST-BROCHURE-' + uuid4().hex
    ids = [prefix+f'-{i:03}' for i in range(len(candidates))]
    keys = []
    headers = auth('superadmin')
    try:
        yield manifest,candidates,ids,keys,headers
    finally:
        assert test_db.name == 'iraseth_test'
        test_db.products.delete_many({'id':{'$in':ids}})
        test_db.catalog_events.delete_many({'product_id':{'$in':ids}})
        test_db.brochure_imports.delete_many({'key':{'$in':keys}})


def test_actual_124_clear_sources_approve_without_inventory_or_price_changes(client,test_db,actual_import):
    manifest,candidates,ids,keys,headers = actual_import
    assert len(candidates) == 124
    stock_before = {name:fingerprint(test_db[name]) for name in STOCK_COLLECTIONS}
    original_products = fingerprint(test_db.products)
    images_included = 0
    selected = []
    for row,pid in zip(candidates,ids):
        paths = row['image_paths']
        valid = bool(paths) and all(valid_image('data:image/png;base64,'+base64.b64encode((FOLDER/path).read_bytes()).decode()) for path in paths)
        images_included += len(paths) if valid else 0
        selected.append({'candidate_id':row['candidate_id'],'id':pid,'unit':'QA_TEST_UNIT',
            'review_confirmed':True,'duplicate_reviewed':True,'review_notes':
            'ISOLATED QA ONLY: simulated staff review of distinct documented source item/variant; identifiers and unit are disposable fixtures.',
            'include_images':valid,'images_reviewed':valid,'image_decision':'include' if valid else 'omit',
            'model_decision':'use_documented' if assess(row)['documented_models'] else 'not_documented'})
    for start in range(0,len(selected),30):
        batch = selected[start:start+30]
        dry = client.post('/api/v2/brochure/dry-run',headers=headers,json={'selections':batch})
        assert dry.status_code == 200, dry.get_json()
        assert not test_db.products.find_one({'id':{'$in':[s['id'] for s in batch]}})
        for item in dry.get_json()['products']:
            assert item['manufacturer'] == ''
            assert item['publicPrice'] is None and item['quantity'] == 0
        key=uuid4().hex;keys.append(key)
        body={'selections':batch,'approval_token':dry.get_json()['approval_token'],'approved':True}
        response=client.post('/api/v2/brochure/approve',headers={**headers,'Idempotency-Key':key},json=body)
        assert response.status_code == 201, response.get_json()
        assert client.post('/api/v2/brochure/approve',headers={**headers,'Idempotency-Key':key},json=body).get_json()['product_ids'] == response.get_json()['product_ids']
    assert test_db.products.count_documents({'id':{'$in':ids}}) == 124
    assert test_db.catalog_events.count_documents({'product_id':{'$in':ids},'action':'brochure_import'}) == 124
    assert len({p['_brochure_identity'] for p in test_db.products.find({'id':{'$in':ids}})}) == 124
    assert {name:fingerprint(test_db[name]) for name in STOCK_COLLECTIONS} == stock_before
    assert fingerprint(test_db.products,{'id':{'$nin':ids}}) == original_products
    for row,pid in zip(candidates,ids):
        stored=test_db.products.find_one({'id':pid})
        assert stored['manufacturer'] == ''
        assert stored['brand'] == (row['documented_brand'] or '')
        assert stored['description'] == row['description']
        assert stored['key_features'] == row['key_features']
        assert stored['specifications'] == row['specifications']
        assert stored['quantity'] == stored['baseline_qty'] == 0
        public=client.get('/api/public/products/'+pid).get_json()
        assert public['name'] == row['name']
        assert public['brand'] == (row['documented_brand'] or '') and public['manufacturer'] == ''
        assert public['imageUrls'] == stored['images']
        assert public['publicPrice'] is None and public['inStock'] is False
        assert not set(public) & {'quantity','price','cost','supplier','brochure_source','_brochure_identity','_id'}
        assert classify(row,[stored])['match_status'] == 'Existing'
    # Exercise the real public pagination contract, including items after 100.
    found=set();page=1
    while True:
        result=client.get(f'/api/public/products?page={page}&limit=100').get_json()
        found.update(p['id'] for p in result['products'])
        if not result['hasMore']:break
        page+=1
    assert page>=2 and set(ids)<=found
    # A new key cannot import an existing source again.
    assert client.post('/api/v2/brochure/dry-run',headers=headers,json={'selections':[selected[0]]}).status_code == 409
    print(f'Actual source integration: 124 products, {images_included} images, 5 approved batches, 124 audit events; all retries idempotent, original products and nine inventory/order/invoice collections unchanged.')


def test_actual_review_distinguishes_source_from_missing_staff_approval():
    manifest,_=load_manifest()
    assessments=[assess(c) for c in manifest['candidates']]
    assert sum(r['source_ready'] for r in assessments)==124
    assert sum(r['source_status']=='Source clarification required' for r in assessments)==11
    assert sum(r['source_status']=='Family / offering' for r in assessments)==131
    assert sum(r['ready_to_import'] for r in assessments)==0
    assert sum(bool(r['documented_models']) for r in assessments)==4
    assert all(r['missing_identity']==['Staff-approved SKU / product ID','Staff-approved selling unit'] for r in assessments)


@pytest.mark.parametrize('name', ['Glucoseth','Polyflex - PUR Catheter Option','Polyflon - PUR Catheter Option',
    'Rapiquick Chlamydia Trachomatics Rapid Test Kit','Chikugunya Rapid Test Kit','Hepatits A Rapid Test Kit',
    'Rapiquick HIV 1/2 Rapid Test Cassette','Rapiquick HIV 1/2 Rapid Test Strips','Rapiquick Syphilis Rapid Test Cassette',
    'Rapiquick Syphilis Rapid Test Strips','Rapiquick Bacterial Vaginosis (Variety)'])
def test_actual_conflicts_cannot_be_approved_by_generic_checkbox(client,auth,test_db,name):
    manifest,_=load_manifest();row=next(c for c in manifest['candidates'] if c['name']==name)
    pid='PYTEST-HOLD-'+uuid4().hex
    result=client.post('/api/v2/brochure/dry-run',headers=auth('subadmin'),json={'selections':[{
        'candidate_id':row['candidate_id'],'id':pid,'unit':'QA_TEST_UNIT','review_confirmed':True,
        'duplicate_reviewed':True,'review_notes':'Simulated approval must not bypass unresolved source conflicts.'}]})
    assert result.status_code==409
    assert 'Source clarification required' in result.get_json()['error']
    assert not test_db.products.find_one({'id':pid})
