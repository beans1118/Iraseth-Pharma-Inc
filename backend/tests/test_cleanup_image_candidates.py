"""Real source-image candidates, tested only against disposable test products."""
import base64
import hashlib
import json
from pathlib import Path

import pytest

from modules.product_metadata import valid_image, identity_pending
from test_pdf_products_existing_system import pdf_products, snapshot  # noqa: F401

ROOT=Path(__file__).resolve().parents[2]


def proposal():
    return json.loads((ROOT/'docs/product-ui-cleanup/image-mapping-proposal.json').read_text(encoding='utf-8'))


def payload(row):
    data=(ROOT/row['candidate']).read_bytes()
    assert len(data)==row['bytes']<=200000
    assert hashlib.sha256(data).hexdigest()==row['candidate_sha256']
    assert hashlib.sha256((ROOT/row['source']).read_bytes()).hexdigest()==row['source_sha256']
    value='data:image/webp;base64,'+base64.b64encode(data).decode()
    assert valid_image(value)
    return value


@pytest.mark.parametrize('index',[0,1])
def test_actual_alpha_care_candidates_use_existing_editor_without_stock_or_identity_changes(index,client,auth,test_db,pdf_products):
    assert test_db.name=='iraseth_test'
    item=proposal()['products'][index]
    _,_,_,create,_=pdf_products
    _,_,docs,_=create([item['name']]);pid=docs[0]['id'];assert pid==item['id']
    original=test_db.products.find_one({'id':pid});before=snapshot(test_db)
    images=[payload(row) for row in item['images']]
    data={'image':images[0],'images':images}
    assert client.put('/api/products/'+pid,json=data,headers=auth('admin')).status_code==403
    response=client.put('/api/products/'+pid,json=data,headers=auth('subadmin'))
    assert response.status_code==200,response.get_json()
    updated=test_db.products.find_one({'id':pid})
    assert updated['images']==images and updated['image']==images[0] and identity_pending(updated)
    for key in original:
        if key not in ('image','images'):assert updated[key]==original[key]
    public=client.get('/api/public/products/'+pid).get_json()
    assert public['imageUrls']==images and public['imageUrl']==images[0]
    assert public['description']==original['description'] and public['inStock'] is False and public['publicPrice'] is None
    assert snapshot(test_db)==before
