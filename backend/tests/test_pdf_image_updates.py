"""Audited image-only updates use real source assets; writes are test-only."""
import base64
import hashlib
import json
from pathlib import Path

import pytest
from bson.json_util import dumps

from routes.products import update_product_images, product_image_state, ProductProblem
from test_pdf_products_existing_system import pdf_products, snapshot  # noqa: F401
from test_product_metadata import metadata_product, image  # noqa: F401

ROOT=Path(__file__).resolve().parents[2]


def reviewed_rows():
    return json.loads((ROOT/'docs/product-images/image-audit-and-plan.json').read_text())['proposed_updates']


def urls(row):
    values=[]
    for entry in row['files']:
        payload=(ROOT/entry['candidate']).read_bytes()
        assert hashlib.sha256(payload).hexdigest()==entry['candidate_sha256']
        values.append('data:image/webp;base64,'+base64.b64encode(payload).decode())
    return values


@pytest.mark.parametrize('index',[0,1,2])
def test_real_verified_images_preserve_all_non_image_data_and_retry_without_new_audit(index,client,test_db,pdf_products):
    assert test_db.name=='iraseth_test'
    row=reviewed_rows()[index];_,_,_,create,actor=pdf_products
    _,_,docs,_=create([row['name']]);pid=docs[0]['id'];assert pid==row['id']
    before=test_db.products.find_one({'id':pid});stock=snapshot(test_db)
    expected=product_image_state(before);images=urls(row)
    result=update_product_images(pid,{'images':images},actor,expected_state=expected,
        source_review={'source_page':row['page'],'evidence':row['evidence']})
    assert result['changed'] is True
    current=test_db.products.find_one({'id':pid})
    assert current['image']==images[0] and current['images']==images
    assert {k:v for k,v in before.items() if k not in ('image','images')}=={k:v for k,v in current.items() if k not in ('image','images')}
    assert snapshot(test_db)==stock
    event=test_db.catalog_events.find_one({'id':result['event_id']})
    assert event['action']=='product_images_updated' and event['actor_email']==actor
    assert event['source_review']['source_page']==row['page'] and event['after_image_hash']==product_image_state(current)
    repeat=update_product_images(pid,{'images':images},actor,expected_state=expected)
    assert repeat['changed'] is False and repeat['event_id'] is None
    assert test_db.catalog_events.count_documents({'product_id':pid,'action':'product_images_updated'})==1
    public=client.get('/api/public/products/'+pid).get_json()
    assert public['imageUrls']==images and public['imageUrl']==images[0]
    assert public['inStock'] is False and public['publicPrice'] is None


def test_image_only_service_rejects_non_image_fields_inactive_roles_and_stale_gallery(test_db,pdf_products,accounts):
    _,_,_,create,actor=pdf_products;_,_,docs,_=create(['Microfusion Set']);pid=docs[0]['id']
    before=dumps(test_db.products.find_one({'id':pid}),sort_keys=True)
    with pytest.raises(ProductProblem,match='fields only'):update_product_images(pid,{'images':[],'quantity':9},actor)
    with pytest.raises(ProductProblem) as denied:update_product_images(pid,{'images':[]},accounts['admin']['email'])
    assert denied.value.status==403
    with pytest.raises(ProductProblem,match='gallery changed'):update_product_images(pid,{'images':[]},actor,expected_state='stale')
    assert dumps(test_db.products.find_one({'id':pid}),sort_keys=True)==before
    assert test_db.catalog_events.count_documents({'product_id':pid,'action':'product_images_updated'})==0


def test_legacy_primary_image_request_preserves_existing_additional_gallery(client,test_db,metadata_product):
    pid,headers,data=metadata_product
    first,second,new=image('red'),image('blue'),image('white')
    assert client.post('/api/products',json={**data,'images':[first,second]},headers=headers).status_code==201
    response=client.put('/api/products/'+pid,json={'image':new},headers=headers)
    assert response.status_code==200,response.get_json()
    assert response.get_json()['images']==[new,second]
    assert test_db.catalog_events.count_documents({'product_id':pid,'action':'product_images_updated'})==1


def test_shared_transaction_rolls_back_images_and_audits_on_a_later_invalid_image(test_db,pdf_products):
    _,_,_,create,actor=pdf_products;rows=reviewed_rows()[:2]
    create([row['name'] for row in rows]);before=snapshot(test_db,['products','catalog_events'])
    with test_db.client.start_session() as session:
        def change(tx):
            update_product_images(rows[0]['id'],{'images':urls(rows[0])},actor,session=tx)
            update_product_images(rows[1]['id'],{'images':['invalid']},actor,session=tx)
        with pytest.raises(ProductProblem):session.with_transaction(change)
    assert snapshot(test_db,['products','catalog_events'])==before
