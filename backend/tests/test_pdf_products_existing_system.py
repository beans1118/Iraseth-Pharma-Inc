"""Actual PDF -> ordinary products -> existing APIs. Writes only iraseth_test.

QA confirmation values/receipts are disposable simulations, never proposed live
SKU/unit mappings, approved prices or physical inventory.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
from datetime import date,timedelta
from decimal import Decimal

from bson.json_util import dumps
import pytest
from config import Config
from modules.brochure.service import load_manifest,FOLDER,provisional_product_id
from modules.brochure.assessment import assess
from modules.product_metadata import PENDING_UNIT
from tools.add_pdf_products import build_plan,apply_plan

STOCK=('inventory_batches','stock_movements','stock_reservations','inventory_logs','inventory_operations','inventory_adjustments','orders','invoices','invoice_events')


def snapshot(db,names=STOCK):
    return {n:hashlib.sha256(dumps(list(db[n].find().sort('_id',1)),sort_keys=True).encode()).hexdigest() for n in names}


@pytest.fixture
def pdf_products(test_db,accounts,monkeypatch):
    assert test_db.name=='iraseth_test'
    monkeypatch.setattr(Config,'BATCH_MODE',True)
    manifest,_=load_manifest();review=json.loads((FOLDER/'pdf-product-image-review.json').read_text())
    candidates=[c for c in manifest['candidates'] if assess(c)['source_ready']]
    ids=[provisional_product_id(manifest,c) for c in candidates]
    assert not test_db.products.count_documents({'id':{'$in':ids}}),'Refusing to overwrite existing PDF test records'
    actor=accounts['subadmin']['email']
    def create(names,duplicate_reviews=None):
        keys=[next(c['candidate_id'] for c in candidates if c['name']==name) for name in names]
        plan,docs=build_plan(manifest,keys,review,duplicate_reviews)
        result=apply_plan(manifest,keys,review,plan,actor,duplicate_reviews)
        return keys,plan,docs,result
    try:yield manifest,review,candidates,create,actor
    finally:
        orders=[o['id'] for o in test_db.orders.find({'lines.id':{'$in':ids}},{'id':1})]
        refs=[q['id'] for q in test_db.quotations.find({'items.id':{'$in':ids}},{'id':1})]
        invoices=[i['id'] for i in test_db.invoices.find({'lines.id':{'$in':ids}},{'id':1})]
        test_db.stock_reservations.delete_many({'product_id':{'$in':ids}})
        test_db.stock_movements.delete_many({'product_id':{'$in':ids}})
        test_db.inventory_batches.delete_many({'product_id':{'$in':ids}})
        test_db.inventory_logs.delete_many({'product_id':{'$in':ids}})
        test_db.inventory_operations.delete_many({'actor_email':actor})
        test_db.orders.delete_many({'id':{'$in':orders}})
        test_db.quotations.delete_many({'id':{'$in':refs}})
        test_db.quotation_events.delete_many({'reference':{'$in':refs}})
        test_db.invoices.delete_many({'id':{'$in':invoices}})
        test_db.invoice_events.delete_many({'invoice_id':{'$in':invoices}})
        test_db.catalog_events.delete_many({'product_id':{'$in':ids}})
        test_db.products.delete_many({'id':{'$in':ids}})


def test_all_124_actual_sources_use_existing_products_and_public_catalog(client,test_db,pdf_products):
    manifest,review,candidates,_,actor=pdf_products
    assert len(candidates)==124
    before=snapshot(test_db);other_products=snapshot(test_db,['products'])['products'];all_ids=[];images=0
    for start in range(0,len(candidates),30):
        names=[c['name'] for c in candidates[start:start+30]]
        duplicate_reviews={c['candidate_id']:'ISOLATED QA ONLY: deliberate review of distinct printed source names/variants; never a live import authorization.' for c in candidates[start:start+30]}
        keys,plan,docs,result=pdf_products[3](names,duplicate_reviews)
        assert len(result['created_ids'])==len(names)
        all_ids+=result['created_ids'];images+=sum(len(d['images']) for d in docs)
        # Repeating the exact reviewed operation only reports existing IDs.
        repeat=apply_plan(manifest,keys,review,plan,actor,duplicate_reviews)
        assert repeat['created_ids']==[] and set(repeat['already_existing_ids'])==set(result['created_ids'])
    assert images==8
    assert snapshot(test_db)==before
    assert snapshot_filtered(test_db.products,{'id':{'$nin':all_ids}})==other_products
    assert test_db.catalog_events.count_documents({'product_id':{'$in':all_ids},'action':'pdf_product_create'})==124
    public=[];page=1
    while True:
        body=client.get(f'/api/public/products?page={page}&limit=100').get_json();public+=body['products']
        if not body['hasMore']:break
        page+=1
    by_id={p['id']:p for p in public}
    for candidate in candidates:
        pid=provisional_product_id(manifest,candidate);doc=test_db.products.find_one({'id':pid});p=by_id[pid]
        assert doc['quantity']==doc['baseline_qty']==0 and doc['price'] is None and doc['storefront_price'] is None
        assert doc['identity_status']=='provisional' and doc['sku']=='' and doc['unit']==PENDING_UNIT
        assert p['name']==candidate['name'] and p['description']==candidate['description']
        assert p['keyFeatures']==candidate['key_features'] and p['specifications']==candidate['specifications']
        assert p['publicPrice'] is None and p['inStock'] is False and p['slug']==pid
        assert p['manufacturer']=='' and 'sku' not in p and 'identity_status' not in p


def snapshot_filtered(collection,query):
    return hashlib.sha256(dumps(list(collection.find(query).sort('_id',1)),sort_keys=True).encode()).hexdigest()


def test_pending_identity_blocks_stock_orders_invoices_and_public_prices(client,auth,test_db,pdf_products,monkeypatch):
    _,_,_,create,_=pdf_products;_,_,docs,_=create(['Microfusion Set']);pid=docs[0]['id'];h=auth('subadmin')
    before=snapshot(test_db)
    receipt={'product_id':pid,'lot':'QA-LOT','expires_on':(date.today()+timedelta(days=90)).isoformat(),'qty':2}
    r=client.post('/api/v2/inventory/batches/receive',json=receipt,headers={**h,'Idempotency-Key':uuid4().hex})
    assert r.status_code==409 and 'genuine SKU' in r.get_json()['error']
    assert client.post('/api/orders',json={'client':'QA','email':'qa@example.invalid','facility':'QA','lines':[{'id':pid,'qty':1}]}).status_code==409
    assert client.post('/api/v2/invoices',json={'client':'QA','email':'qa@example.invalid','facility':'QA','lines':[{'id':pid,'qty':1,'price':'1.00'}]},headers={**h,'Idempotency-Key':uuid4().hex}).status_code==400
    assert client.patch('/api/products/'+pid+'/storefront',json={'publicPrice':1},headers=auth('superadmin')).status_code==409
    assert client.put('/api/products/'+pid,json={'identity_status':'confirmed'},headers=h).status_code==400
    assert client.put('/api/products/'+pid,json={'unit':'QA_TEST_UNIT'},headers=h).status_code==200
    assert client.post('/api/v2/inventory/batches/receive',json=receipt,headers={**h,'Idempotency-Key':uuid4().hex}).status_code==409
    monkeypatch.setattr(Config,'BATCH_MODE',False)
    assert client.post('/api/inventory/'+pid+'/supply',json={'qty':2},headers=h).status_code==409
    assert snapshot(test_db)==before


def test_existing_editor_confirms_real_identity_without_rekey_and_receives_normally(client,auth,test_db,pdf_products,product_factory):
    _,_,_,create,_=pdf_products;_,_,docs,_=create(['Microfusion Set']);pid=docs[0]['id'];h=auth('subadmin')
    assert client.put('/api/products/'+pid,json={'description':'QA metadata edit'},headers=h).status_code==200
    duplicate=product_factory();payload={'sku':duplicate.lower(),'unit':'QA_TEST_UNIT','confirm_identity':True,'identity_review_note':'ISOLATED QA ONLY: simulated SKU/unit confirmation.'}
    assert client.put('/api/products/'+pid,json=payload,headers=h).status_code==409
    payload['sku']='PYTEST-CONFIRMED-'+uuid4().hex
    assert client.put('/api/products/'+pid,json=payload,headers=auth('admin')).status_code==403
    assert client.put('/api/products/'+pid,json={**payload,'unit':PENDING_UNIT},headers=h).status_code==400
    r=client.put('/api/products/'+pid,json=payload,headers=h);assert r.status_code==200,r.get_json()
    p=r.get_json();assert p['id']==pid and p['identity_status']=='confirmed' and p['price'] is None
    assert client.get('/api/public/products/'+pid).get_json()['slug']==pid
    assert client.get('/api/products?q='+payload['sku'],headers=h).get_json()[0]['id']==pid
    assert client.put('/api/products/'+pid,json={'id':pid,'description':'Another metadata edit'},headers=h).status_code==200
    assert test_db.products.find_one({'id':pid})['_sku_key']==payload['sku'].casefold()
    assert client.post('/api/products',json={'id':payload['sku'].lower(),'name':'QA duplicate SKU','category':'QA','unit':'QA_TEST_UNIT','description':'','quantity':0},headers=h).status_code==409
    receipt=client.post('/api/v2/inventory/batches/receive',json={'product_id':pid,'lot':'QA-LOT','expires_on':(date.today()+timedelta(days=90)).isoformat(),'qty':2},headers={**h,'Idempotency-Key':uuid4().hex})
    assert receipt.status_code==201,receipt.get_json()
    assert client.get('/api/public/products/'+pid).get_json()['inStock'] is True
    assert client.get('/api/public/products/'+pid).get_json()['publicPrice'] is None


def test_unpriced_pdf_inquiry_acceptance_reservation_fulfillment_and_invoice(client,auth,test_db,pdf_products):
    _,_,_,create,_=pdf_products;_,_,docs,_=create(['Microfusion Set']);pid=docs[0]['id'];h=auth('subadmin')
    mapping={'sku':'PYTEST-CONFIRMED-'+uuid4().hex,'unit':'QA_TEST_UNIT','confirm_identity':True,'identity_review_note':'ISOLATED QA ONLY: not a proposed live SKU/unit mapping.'}
    assert client.put('/api/products/'+pid,json=mapping,headers=h).status_code==200
    assert client.post('/api/v2/inventory/batches/receive',json={'product_id':pid,'lot':'QA-LOT','expires_on':(date.today()+timedelta(days=90)).isoformat(),'qty':2},headers={**h,'Idempotency-Key':uuid4().hex}).status_code==201
    from test_quotations_phase3 import payload
    client.environ_base['REMOTE_ADDR']='pdf-qa-'+uuid4().hex
    q=client.post('/api/public/quotations',json=payload(pid),headers={'Idempotency-Key':uuid4().hex});assert q.status_code==201,q.get_json()
    ref=q.get_json()['reference'];accepted=client.post('/api/v2/quotations/'+ref+'/accept',headers=h);assert accepted.status_code==200,accepted.get_json()
    oid=accepted.get_json()['order_id'];order=test_db.orders.find_one({'id':oid})
    assert order['total'] is None and order['lines'][0]['price'] is None and order['lines'][0]['lineTotal'] is None
    for action in ('approve','fulfill'):
        result=client.post('/api/v2/orders/'+oid+'/'+action,headers={**h,'Idempotency-Key':uuid4().hex});assert result.status_code==200,result.get_json()
    qty=order['lines'][0]['qty'];assert test_db.products.find_one({'id':pid})['quantity']==2-qty
    invoice=client.post('/api/v2/invoices',json={'order_id':oid,'lines':[{'id':pid,'qty':qty,'price':'7.50'}]},headers={**h,'Idempotency-Key':uuid4().hex})
    assert invoice.status_code==201,invoice.get_json()
    assert invoice.get_json()['total']==str(Decimal('7.50')*qty)


def test_dry_run_does_not_start_flask_write_records_or_create_indexes(test_db,pdf_products,tmp_path):
    m,_,candidates,_,_=pdf_products
    key=next(c['candidate_id'] for c in candidates if c['name']=='Microfusion Set')
    before=snapshot(test_db,STOCK+('products','catalog_events'));indexes=test_db.products.index_information()
    r=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'tools/add_pdf_products.py'),'--database','iraseth_test','--candidate-id',key,'--report',str(tmp_path/'dry.json')],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert json.loads(r.stdout)['products'][0]['price'] is None
    assert snapshot(test_db,STOCK+('products','catalog_events'))==before
    assert test_db.products.index_information()==indexes


def test_source_holds_families_and_changed_reviewed_report_are_rejected(test_db,pdf_products):
    m,review,candidates,_,_=pdf_products
    held=next(c for c in m['candidates'] if c['name']=='Glucoseth')
    with pytest.raises(ValueError,match='ambiguous'):build_plan(m,[held['candidate_id']],review)
    family=next(c for c in m['candidates'] if c['candidate_type']=='product_family')
    with pytest.raises(ValueError,match='family'):build_plan(m,[family['candidate_id']],review)
    key=candidates[0]['candidate_id'];plan,_=build_plan(m,[key],review)
    with pytest.raises(ValueError,match='report'):apply_plan(m,[key],review,{**plan,'database':'iraseth_dev'},'nonexistent@example.invalid')


def test_similar_source_names_need_explicit_duplicate_review(test_db,pdf_products):
    m,review,candidates,_,_=pdf_products
    keys=[next(c['candidate_id'] for c in candidates if c['name']==name) for name in ('Autofusion Set','Autofusion Set - Y Injection Port')]
    before=snapshot(test_db,['products','catalog_events'])
    with pytest.raises(ValueError,match='possible duplicates'):build_plan(m,keys,review)
    assert snapshot(test_db,['products','catalog_events'])==before


def test_two_products_cannot_confirm_the_same_sku_concurrently(client,auth,test_db,pdf_products):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    _,_,_,create,_=pdf_products;_,_,docs,_=create(['Microfusion Set','Polyvol']);h=auth('subadmin')
    barrier=Barrier(2);sku='PYTEST-RACE-'+uuid4().hex
    def confirm(doc):
        with client.application.test_client() as c:
            barrier.wait(timeout=10)
            return c.put('/api/products/'+doc['id'],headers=h,json={'sku':sku,'unit':'QA_TEST_UNIT','confirm_identity':True,'identity_review_note':'ISOLATED QA ONLY: concurrent duplicate guard test.'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(confirm,docs))
    assert sorted(statuses)==[200,409]
    assert test_db.products.count_documents({'sku':sku})==1


def test_remote_or_production_targets_are_refused_before_any_write():
    from tools.add_pdf_products import validate_local_target
    with pytest.raises(ValueError,match='production'):validate_local_target('iraseth_dev','mongodb+srv://example.mongodb.net/')
    with pytest.raises(ValueError,match='production'):validate_local_target('iraseth_production','mongodb://127.0.0.1:27017/')
