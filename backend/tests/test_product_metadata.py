import base64
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image


def image(color='white', kind='PNG'):
    output = BytesIO()
    Image.new('RGB', (20,20), color).save(output, format=kind)
    mime = {'PNG':'png','JPEG':'jpeg','WEBP':'webp'}[kind]
    return f'data:image/{mime};base64,' + base64.b64encode(output.getvalue()).decode()


@pytest.fixture
def metadata_product(client, auth, test_db):
    pid = 'PYTEST-METADATA-' + uuid4().hex
    headers = auth('subadmin')
    data = {'id':pid, 'name':'Metadata sample', 'category':'Testing', 'unit':'Box', 'description':'Documented text', 'quantity':0}
    try:
        yield pid, headers, data
    finally:
        test_db.products.delete_many({'id':pid})
        test_db.catalog_events.delete_many({'product_id':pid})


def test_gallery_create_edit_and_public_allowlist(client, test_db, metadata_product):
    pid, headers, data = metadata_product
    first, second = image(), image('red','WEBP')
    data.update(images=[first,second], key_features=['Documented feature'], specifications=[{'label':'Pack size','value':'Documented value'}])
    response = client.post('/api/products', headers=headers, json=data)
    assert response.status_code == 201, response.get_json()
    assert response.get_json()['image'] == first
    before = test_db.products.find_one({'id':pid})
    test_db.products.update_one({'id':pid}, {'$set': {'cost': 123, 'supplier': 'private', 'stock_notes':'secret'}})
    response = client.put(f'/api/products/{pid}', headers=headers, json={'images':[second,first], 'quantity':500})
    assert response.status_code == 200
    assert response.get_json()['image'] == second
    assert response.get_json()['quantity'] == before['quantity'] == 0
    assert test_db.inventory_batches.count_documents({'product_id':pid}) == 0
    assert test_db.stock_movements.count_documents({'product_id':pid}) == 0
    public = client.get(f'/api/public/products/{pid}').get_json()
    assert public['imageUrl'] == second and public['imageUrls'] == [second,first]
    assert public['keyFeatures'] == ['Documented feature']
    assert public['specifications'] == [{'label':'Pack size','value':'Documented value'}]
    assert public['publicPrice'] is None and public['inStock'] is False
    assert not set(public) & {'cost','supplier','stock_notes','quantity','price','reserved','_id'}
    assert client.put(f'/api/products/{pid}', headers=headers, json={'images':[]}).get_json()['image'] == ''
    assert client.get(f'/api/public/products/{pid}').get_json()['imageUrls'] == []


@pytest.mark.parametrize('kind',['PNG','JPEG','WEBP'])
def test_single_image_backward_compatibility(client, test_db, metadata_product, kind):
    pid, headers, data = metadata_product
    old = image(kind=kind)
    data['image'] = old
    assert client.post('/api/products', headers=headers, json=data).status_code == 201
    test_db.products.update_one({'id':pid}, {'$unset': {'images':'', 'key_features':'', 'specifications':''}})
    public = client.get(f'/api/public/products/{pid}').get_json()
    assert public['imageUrl'] == old and public['imageUrls'] == [old]
    assert public['keyFeatures'] == [] and public['specifications'] == []


@pytest.mark.parametrize('fields',[
    {'images':['data:image/svg+xml;base64,PHN2Zz4=']}, {'images':['https://external.invalid/pic.jpg']},
    {'images':['data:image/png;base64,aGVsbG8=']}, {'images':['data:image/png;base64,%%%']},
    {'images':'not a list'}, {'images':[None]}, {'images':['']},
    {'images':[image()]*9}, {'images':[image(),image()]},
    {'key_features':['']}, {'key_features':'a'}, {'key_features':[{'private':'not text'}]},
    {'specifications':[{'label':'','value':'x'}]}, {'specifications':[{'label':'x','value':'v','secret':True}]},
    {'image':'data:image/png;base64,' + base64.b64encode(b'x'*200001).decode()},
    {'images':['data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()]},
])
def test_malformed_gallery_or_metadata_rejected(client, test_db, metadata_product, fields):
    pid, headers, data = metadata_product
    data.update(fields)
    result = client.post('/api/products', headers=headers, json=data)
    assert result.status_code == 400, result.get_json()
    assert test_db.products.count_documents({'id':pid}) == 0
    assert test_db.inventory_batches.count_documents({'product_id':pid}) == 0


def test_metadata_permissions_and_inventory_unchanged(client, auth, test_db, metadata_product, monkeypatch):
    from config import Config
    pid, headers, data = metadata_product
    monkeypatch.setattr(Config,'BATCH_MODE',True)
    assert client.post('/api/products', headers=headers, json=data).status_code == 201
    url = f'/api/products/{pid}'
    assert client.put(url, json={'images':[]}).status_code == 401
    assert client.put(url, headers=auth('admin'), json={'images':[]}).status_code == 403
    before = test_db.products.find_one({'id':pid})
    assert client.put(url, headers=headers, json={'description':'Updated documentation','quantity':999,'price':0}).status_code == 200
    after = test_db.products.find_one({'id':pid})
    for key in ['quantity','baseline_qty','storefront_price','storefront_visible']:
        assert before[key] == after[key]
    assert client.put(url, headers=headers, json={'id':'new-id'}).status_code == 409


def test_mime_spoofing_and_pixel_bomb():
    from modules.product_metadata import valid_image
    assert not valid_image(image().replace('image/png','image/jpeg'))
    output = BytesIO()
    Image.new('1',(5000,5000)).save(output,format='PNG')
    assert not valid_image('data:image/png;base64,'+base64.b64encode(output.getvalue()).decode())


def test_documented_brand_and_manufacturer_remain_separate(client, test_db, metadata_product):
    pid, headers, data = metadata_product
    data.update(brand='Documented Brand', manufacturer='Documented Manufacturer')
    assert client.post('/api/products',headers=headers,json=data).status_code == 201
    result=client.get('/api/public/products/'+pid).get_json()
    assert result['brand'] == 'Documented Brand'
    assert result['manufacturer'] == 'Documented Manufacturer'
    listed=client.get('/api/public/products?limit=200').get_json()['products']
    row=next(p for p in listed if p['id']==pid)
    assert row['brand'] == 'Documented Brand' and row['manufacturer'] == 'Documented Manufacturer'
    # A legacy combined brand/manufacturer value remains a brand fallback;
    # it does not become a new claim that the value is a documented maker.
    test_db.products.update_one({'id':pid},{'$unset':{'brand':''}})
    legacy=client.get('/api/public/products/'+pid).get_json()
    assert legacy['brand'] == 'Documented Manufacturer' and legacy['manufacturer'] == ''


def test_sku_comparison_key_preserves_id_and_blocks_legacy_case_duplicates(client,test_db,metadata_product):
    pid,headers,data=metadata_product
    alternate=pid.lower()
    try:
        # Legacy records are protected by a read-only compatibility check, with
        # no backfill. New records also have the unique comparison-key index.
        test_db.products.insert_one({**data,'id':alternate})
        assert client.post('/api/products',headers=headers,json=data).status_code==409
        test_db.products.delete_one({'id':alternate})
        created=client.post('/api/products',headers=headers,json=data)
        assert created.status_code==201 and created.get_json()['id']==pid
        assert client.post('/api/products',headers=headers,json={**data,'id':alternate}).status_code==409
        assert '_sku_key' not in client.get('/api/public/products/'+pid).get_json()
    finally:
        test_db.products.delete_one({'id':alternate})
