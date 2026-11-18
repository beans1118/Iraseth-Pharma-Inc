import csv
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import StringIO
from uuid import uuid4

import pytest
from modules.brochure import routes as brochure
from modules.brochure.review_sheet import mapping_csv, mapping_rows, refresh_mapping_file
from modules.brochure.service import FOLDER, load_manifest, digest
from modules.product_metadata import canonical_sku
from test_brochure_import import source, dry, approve


def test_template_has_exact_124_candidates_and_complete_source_context():
    manifest,_=load_manifest()
    rows=list(csv.DictReader(StringIO(mapping_csv(manifest,FOLDER).lstrip('\ufeff'))))
    assert len(rows)==len({r['candidate_id'] for r in rows})==124
    by_id={c['candidate_id']:c for c in manifest['candidates']}
    for row in rows:
        item=by_id[row['candidate_id']]
        assert row['source_pdf']==manifest['source_pdf']
        assert int(row['source_pdf_page'])==item['source_pdf_page']
        assert row['name']==item['name'] and row['category']==item['category']
        import json
        assert json.loads(row['key_features'])==item['key_features']
        assert json.loads(row['specifications'])==item['specifications']
        assert json.loads(row['source_image_paths'])==item['image_paths']
        assert json.loads(row['missing_fields'])
        assert row['image_review_status'] and row['approval_status']=='Pending staff review'
        assert row['staff_approved_sku']==row['staff_approved_selling_unit']==row['staff_verified_model']==''
        assert row['model_decision']==row['image_decision']=='pending'
        assert row['staff_approved']==row['images_approved']==row['include_in_batch']=='false'


def test_refresh_preserves_staff_work_and_rejects_unknown_keys(tmp_path):
    manifest,_=load_manifest();rows=mapping_rows(manifest,FOLDER)
    rows[0].update(staff_approved_sku='QA-STAFF-FIXTURE',staff_approved_selling_unit='QA_UNIT',staff_review_notes='Saved staff draft')
    path=tmp_path/'mapping.csv'
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    refresh_mapping_file(path,manifest,FOLDER)
    with path.open(encoding='utf-8-sig',newline='') as stream:new=list(csv.DictReader(stream))
    assert new[0]['staff_approved_sku']=='QA-STAFF-FIXTURE' and new[0]['staff_review_notes']=='Saved staff draft'
    rows[0]['candidate_id']='unknown-source'
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    before=path.read_bytes()
    with pytest.raises(ValueError):refresh_mapping_file(path,manifest,FOLDER)
    assert path.read_bytes()==before


def test_template_download_requires_session_and_is_read_only(client,auth,test_db):
    assert client.get('/api/v2/brochure/mapping-template').status_code==401
    count=test_db.products.count_documents({})
    response=client.get('/api/v2/brochure/mapping-template',headers=auth('admin'))
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    assert len(list(csv.DictReader(StringIO(response.get_data(as_text=True).lstrip('\ufeff')))))==124
    assert test_db.products.count_documents({})==count


@pytest.mark.parametrize('updates',[
    {'model_decision':'pending'}, {'image_decision':'pending'},
    {'model_decision':'use_documented'},
    {'model_decision':'staff_verified','model':'QA-MODEL','model_evidence':''},
    {'model_decision':'not_documented','model':'fabricated-without-review'},
    {'image_decision':'include','include_images':False},
])
def test_incomplete_model_or_image_review_is_rejected(client,auth,source,updates):
    _,selection=source
    assert dry(client,auth(),{**selection,**updates}).status_code==400


def test_verified_model_is_audited_and_private_evidence_not_public(client,auth,test_db,source):
    _,selection=source
    selection.update(model_decision='staff_verified',model='QA-MODEL',model_evidence='QA fixture supplier document reference')
    headers=auth();run=dry(client,headers,selection)
    assert run.status_code==200 and run.get_json()['products'][0]['model']=='QA-MODEL'
    assert approve(client,headers,selection,run.get_json()['approval_token']).status_code==201
    stored=test_db.products.find_one({'id':selection['id']})
    assert stored['brochure_source']['model_review']['evidence']=='QA fixture supplier document reference'
    public=client.get('/api/public/products/'+selection['id']).get_json()
    assert public['model']=='QA-MODEL' and 'brochure_source' not in public
    assert 'supplier document' not in str(public)


def test_batch_limit_and_unicode_duplicate_skus(client,auth,source):
    _,selection=source;headers=auth()
    assert client.post('/api/v2/brochure/dry-run',headers=headers,json={'selections':[selection]*31}).status_code==400
    assert canonical_sku(' ＡＢＣ-123 ')==canonical_sku('abc-123')


def test_concurrent_case_variant_skus_have_one_winner(client,auth,test_db,source):
    manifest,selection=source;headers=auth()
    second=deepcopy(manifest['candidates'][0]);second['candidate_id']+='-second';second['name']='Separate QA Item '+uuid4().hex
    manifest['candidates'].append(second)
    other={**selection,'candidate_id':second['candidate_id'],'id':selection['id'].lower()}
    runs=[dry(client,headers,s) for s in [selection,other]]
    assert all(r.status_code==200 for r in runs)
    keys=[uuid4().hex,uuid4().hex]
    bodies=[{'selections':[s],'approval_token':r.get_json()['approval_token'],'approved':True} for s,r in zip([selection,other],runs)]
    def submit(i):
        from app import app
        with app.test_client() as c:return c.post('/api/v2/brochure/approve',headers={**headers,'Idempotency-Key':keys[i]},json=bodies[i]).status_code
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:statuses=list(executor.map(submit,[0,1]))
        assert sorted(statuses)==[201,409]
        assert test_db.products.count_documents({'_sku_key':canonical_sku(selection['id'])})==1
    finally:
        test_db.products.delete_many({'id':{'$in':[selection['id'],other['id']]}})
        test_db.catalog_events.delete_many({'product_id':{'$in':[selection['id'],other['id']]}})
        test_db.brochure_imports.delete_many({'key':{'$in':keys}})


def test_standalone_dry_run_cannot_write_or_create_indexes(source,monkeypatch):
    from tools.dry_run_brochure_mapping import validate_read_only
    from pymongo.collection import Collection
    manifest,selection=source
    def forbidden(*args,**kwargs):raise AssertionError('Read-only dry run attempted a database mutation.')
    with monkeypatch.context() as guard:
        for method in ('insert_one','insert_many','update_one','update_many','delete_one','delete_many','create_index','create_indexes','find_one_and_update'):
            guard.setattr(Collection,method,forbidden)
        result=validate_read_only([selection],manifest,[])
    assert result[0]['quantity']==0 and result[0]['publicPrice'] is None
