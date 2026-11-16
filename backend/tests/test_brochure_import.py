from copy import deepcopy
from uuid import uuid4
import pytest

from modules.brochure import routes as brochure
from modules.brochure.service import classify, load_manifest, normalized


@pytest.fixture
def source(client, test_db, monkeypatch):
    marker=uuid4().hex
    candidate={'candidate_id':'review-'+marker,'name':'Unique Device '+marker,'description':'Source-supported description',
        'category':'Testing','key_features':['Source-supported feature'],'specifications':[{'label':'Documented','value':'Value'}],
        'documented_brand':'Documented Brand','documented_manufacturer':None,'source_pdf_page':3,'candidate_type':'individual',
        'importable':True,'gaps':['SKU and unit required'],'review_notes':['Source needs review'],'image_paths':[],'image_review_status':'No image'}
    manifest={'source_pdf':'source.pdf','source_sha256':'a'*64,'page_count':15,'images':[],'candidates':[candidate]}
    monkeypatch.setattr(brochure,'load_manifest',lambda:(deepcopy(manifest),'manifest-'+marker))
    selection={'candidate_id':candidate['candidate_id'],'id':'PYTEST-IMPORT-'+marker,'unit':'Box','review_confirmed':True,
        'review_notes':'Reviewed source and confirmed selling unit; unresolved claims excluded.','duplicate_reviewed':False,'include_images':False,'images_reviewed':False,'model_decision':'not_documented','image_decision':'omit'}
    try:yield manifest,selection
    finally:
        test_db.products.delete_many({'id':{'$regex':'^PYTEST-IMPORT-'+marker}})
        test_db.catalog_events.delete_many({'product_id':{'$regex':'^PYTEST-IMPORT-'+marker}})
        test_db.brochure_imports.delete_many({'selection_hash':brochure.digest([selection])})
        test_db.products.delete_many({'name':candidate['name']})


def dry(client,headers,selection):
    return client.post('/api/v2/brochure/dry-run',headers=headers,json={'selections':[selection]})


def approve(client,headers,selection,token,key=None):
    return client.post('/api/v2/brochure/approve',headers={**headers,'Idempotency-Key':key or uuid4().hex},
        json={'selections':[selection],'approval_token':token,'approved':True})


def test_preview_and_dry_run_never_insert(client,auth,test_db,source):
    manifest,selection=source
    headers=auth('subadmin')
    result=client.get('/api/v2/brochure/preview',headers=headers)
    assert result.status_code==200
    assert result.get_json()['candidates'][0]['match_status']=='New'
    assert result.get_json()['candidates'][0]['status']=='Needs Review'
    result=dry(client,headers,selection)
    assert result.status_code==200,result.get_json()
    assert result.get_json()['dry_run'] is True
    assert result.get_json()['products'][0]['quantity']==0
    assert not test_db.products.find_one({'id':selection['id']})
    assert test_db.inventory_batches.count_documents({'product_id':selection['id']})==0


def test_approved_import_shared_validation_zero_stock_and_retry(client,auth,test_db,source,monkeypatch):
    from config import Config
    monkeypatch.setattr(Config,'BATCH_MODE',True)
    _,selection=source;headers=auth('subadmin')
    token=dry(client,headers,selection).get_json()['approval_token'];key=uuid4().hex
    first=approve(client,headers,selection,token,key)
    assert first.status_code==201,first.get_json()
    assert approve(client,headers,selection,token,key).status_code==201
    doc=test_db.products.find_one({'id':selection['id']})
    assert doc['quantity']==doc['baseline_qty']==0
    assert doc['storefront_price'] is None and doc['storefront_visible'] is True
    assert test_db.products.count_documents({'id':selection['id']})==1
    assert test_db.catalog_events.count_documents({'product_id':selection['id'],'action':'brochure_import'})==1
    for collection in ('inventory_batches','stock_movements','stock_reservations','inventory_logs'):
        assert test_db[collection].count_documents({'product_id':selection['id']})==0
    public=client.get('/api/public/products/'+selection['id']).get_json()
    assert public['publicPrice'] is None and public['inStock'] is False
    assert not set(public)&{'_brochure_identity','brochure_source','quantity','price','cost','supplier'}


def test_rbac_and_no_approval_bypass(client,auth,source):
    _,selection=source
    assert client.get('/api/v2/brochure/preview').status_code==401
    assert client.post('/api/v2/brochure/dry-run',json={}).status_code==401
    admin=auth('admin')
    assert client.get('/api/v2/brochure/preview',headers=admin).status_code==200
    assert dry(client,admin,selection).status_code==403
    assert approve(client,admin,selection,'bad').status_code==403
    headers=auth()
    assert approve(client,headers,selection,'bad').status_code==409
    assert client.post('/api/v2/brochure/approve',headers=headers,json={}).status_code==400


@pytest.mark.parametrize('changed',[
    {'id':''},{'unit':''},{'review_confirmed':False},{'review_notes':''},{'quantity':100},{'price':10},{'images':['invented']},
    {'include_images':True,'images_reviewed':False},
])
def test_missing_information_or_private_mutation_rejected(client,auth,source,changed):
    _,selection=source
    assert dry(client,auth(),{**selection,**changed}).status_code==400


def test_families_cannot_be_imported_and_duplicate_selection(client,auth,source):
    manifest,selection=source;headers=auth()
    assert client.post('/api/v2/brochure/dry-run',headers=headers,json={'selections':[selection,selection]}).status_code==409
    manifest['candidates'][0]['importable']=False
    assert dry(client,headers,selection).status_code==400


def test_existing_match_is_blocked_even_with_override(client,auth,test_db,source):
    manifest,selection=source;headers=auth()
    test_db.products.insert_one({'id':selection['id']+'existing','name':manifest['candidates'][0]['name'],'manufacturer':'Documented Brand'})
    assert dry(client,headers,{**selection,'duplicate_reviewed':True}).status_code==409
    assert client.get('/api/v2/brochure/preview',headers=headers).get_json()['candidates'][0]['status']=='Existing'


def test_dry_run_bound_to_actor_selection_and_catalog(client,auth,test_db,source):
    _,selection=source;headers=auth('subadmin')
    token=dry(client,headers,selection).get_json()['approval_token']
    assert approve(client,auth('superadmin'),selection,token).status_code==409
    assert approve(client,headers,{**selection,'unit':'Other'},token).status_code==409
    test_db.products.insert_one({'id':selection['id']+'stale','name':'Changed catalog'})
    assert approve(client,headers,selection,token).status_code==409
    assert not test_db.products.find_one({'id':selection['id']})


def test_matching_normalizes_brand_and_flags_near_duplicates():
    candidate={'name':'Rapiquick Pregnancy Test','documented_brand':'RAPIQUICK'}
    assert normalized('  Rapiquick / Pregnancy - Test ')=='rapiquick pregnancy test'
    assert classify(candidate,[{'id':'staff-id','name':'RAPIQUICK pregnancy test','manufacturer':'Rapiquick'}])['match_status']=='Existing'
    assert classify(candidate,[{'id':'staff-id','name':'Rapiquick Pregnancy Test Kit','manufacturer':'Rapiquick'}])['match_status']=='Ambiguous'
    assert classify(candidate,[])['match_status']=='New'


def test_approval_token_cannot_cross_database_targets(client,auth,test_db,source):
    _,selection=source;headers=auth()
    result=dry(client,headers,selection)
    assert result.get_json()['database']=='iraseth_test'
    claims=brochure.signer().loads(result.get_json()['approval_token'])
    assert claims['database']=='iraseth_test'
    claims['database']='iraseth_dev'
    wrong_target=brochure.signer().dumps(claims)
    assert approve(client,headers,selection,wrong_target).status_code==409
    assert not test_db.products.find_one({'id':selection['id']})


def test_complete_source_manifest_and_quarantined_claims():
    manifest,_=load_manifest()
    assert manifest['page_count']==15
    assert len(manifest['candidates'])==266
    assert {c['source_pdf_page'] for c in manifest['candidates']}==set(range(3,16))
    assert len({c['candidate_id'] for c in manifest['candidates']})==266
    rapid=[c for c in manifest['candidates'] if c['source_pdf_page']==12]
    assert len(rapid)==82
    assert len([c for c in manifest['candidates'] if c.get('family')=='Alphashot'])==16
    assert len([c for c in manifest['candidates'] if c.get('family')=='Irasafety Syringe'])==8
    assert len([c for c in manifest['candidates'] if c['name'].endswith('PUR Catheter Option')])==2
    for row in manifest['candidates']:
        if row['name'] in ('Polyflex - 22G Blue','Polyflon - 20G Pink'):
            assert all(s['label'] not in ('Optional catheter','Documented size range') for s in row['specifications'])
    glucose=next(c for c in manifest['candidates'] if c['name']=='Glucoseth')
    assert 'centrifuge' not in glucose['description'].lower()
    assert any('POWER CONFLICT' in note for note in glucose['review_notes'])
    assert all(not c['approved'] and c['sku'] is None and c['unit'] is None for c in manifest['candidates'])
