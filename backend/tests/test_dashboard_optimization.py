"""Regression checks for the dashboard optimization backend additions."""
import base64
import uuid
from io import BytesIO
from PIL import Image


def test_product_image_validation(client, auth, test_db):
    suffix = uuid.uuid4().hex
    base = {'id': 'UI-' + suffix, 'name': 'Sample', 'description': '', 'category': 'Medicines',
            'unit': 'Box', 'quantity': 0, 'price': 0, 'manufacturer': ''}
    bad = client.post('/api/products', headers=auth('superadmin'), json={**base, 'image': 'data:image/png;base64,not-base64!!!'})
    assert bad.status_code == 400
    truncated = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'sample').decode()
    assert client.post('/api/products', headers=auth('superadmin'), json={**base, 'image': 'data:image/png;base64,' + truncated}).status_code == 400
    output = BytesIO()
    Image.new('RGB', (1,1), 'white').save(output, format='PNG')
    tiny_png = base64.b64encode(output.getvalue()).decode()
    try:
        ok = client.post('/api/products', headers=auth('superadmin'), json={**base, 'image': 'data:image/png;base64,' + tiny_png})
        assert ok.status_code == 201
        assert ok.get_json()['manufacturer'] == ''
        assert ok.get_json()['image'].startswith('data:image/png;base64,')
    finally:
        test_db.products.delete_one({'id':base['id']})


def test_staff_create_message_requires_auth(client):
    assert client.post('/api/v2/support/staff/threads', json={'order_id':'X', 'body':'Hello'}).status_code == 401


def test_staff_create_message_rejects_missing_order(client, auth):
    r = client.post('/api/v2/support/staff/threads', headers=auth('superadmin'),
                    json={'order_id': 'UNKNOWN-' + uuid.uuid4().hex, 'body':'Hello'})
    assert r.status_code == 404
