"""Phase 3 quotations: isolated UAT/test database fixture, no production records."""
from datetime import date, timedelta
from uuid import uuid4


def setup_product(test_db, stocked=True):
    pid = 'RFQ-PYTEST-' + uuid4().hex
    test_db.products.insert_one({'id': pid, 'name': 'Quotation Test Device', 'category': 'Medical Devices',
                                 'quantity': 0, 'storefront_visible': True, 'storefront_price': 125.50})
    if stocked:
        test_db.inventory_batches.insert_one({'id': uuid4().hex, 'product_id': pid, 'lot': 'RFQ-A',
            'expires_on': (date.today()+timedelta(days=90)).isoformat(),
            'condition': 'available', 'unverified': False, 'on_hand': 5, 'reserved': 0})
    return pid


def payload(pid):
    return {'fullName':'Sample Customer','email':'sample@example.org','phone':'09000000000',
            'company':'Sample Clinic','notes':'Please advise lead time',
            'items':[{'id':pid,'quantity':2}]}


def test_quotation_submit_idempotency_and_no_inventory_writes(client, test_db, monkeypatch):
    from config import Config
    monkeypatch.setattr(Config, 'BATCH_MODE', True)
    pid=setup_product(test_db)
    key='phase3-'+uuid4().hex
    before_orders=test_db.orders.count_documents({})
    before_reservations=test_db.stock_reservations.count_documents({})
    before_movements=test_db.stock_movements.count_documents({})
    try:
        result=client.post('/api/public/quotations',json=payload(pid),headers={'Idempotency-Key':key})
        assert result.status_code==201, result.get_json()
        ref=result.get_json()['reference']
        assert ref.startswith('RFQ-')
        again=client.post('/api/public/quotations',json=payload(pid),headers={'Idempotency-Key':key})
        assert again.status_code==200
        assert again.get_json()['reference']==ref
        assert test_db.quotations.count_documents({'id':ref})==1
        assert test_db.orders.count_documents({})==before_orders
        assert test_db.stock_reservations.count_documents({})==before_reservations
        assert test_db.stock_movements.count_documents({})==before_movements
        assert test_db.inventory_batches.find_one({'product_id':pid})['on_hand']==5
        assert test_db.inventory_batches.find_one({'product_id':pid})['reserved']==0
        wrong=payload(pid);wrong['notes']='Different payload'
        assert client.post('/api/public/quotations',json=wrong,headers={'Idempotency-Key':key}).status_code==409
    finally:
        test_db.quotations.delete_many({'idempotency_key':key})
        test_db.inventory_batches.delete_many({'product_id':pid})
        test_db.products.delete_many({'id':pid})


def test_quotation_rejects_hidden_stockout_invalid_and_anonymous_staff(client,test_db,monkeypatch):
    from config import Config
    monkeypatch.setattr(Config,'BATCH_MODE',True)
    pid=setup_product(test_db,stocked=False)
    try:
        key='phase3-'+uuid4().hex
        result=client.post('/api/public/quotations',json=payload(pid),headers={'Idempotency-Key':key})
        assert result.status_code==400
        assert client.get('/api/v2/quotations').status_code==401
        assert client.patch('/api/v2/quotations/NOPE/status',json={'status':'Closed'}).status_code==401
        test_db.products.update_one({'id':pid},{'$set':{'storefront_visible':False}})
        assert client.post('/api/public/quotations',json=payload(pid),headers={'Idempotency-Key':key}).status_code==400
        assert test_db.quotations.count_documents({'idempotency_key':key})==0
    finally:
        test_db.products.delete_many({'id':pid})


def test_quotation_staff_permissions_and_audit(client,auth,test_db,monkeypatch):
    from config import Config
    monkeypatch.setattr(Config,'BATCH_MODE',True)
    pid=setup_product(test_db)
    key='phase3-'+uuid4().hex
    try:
        created=client.post('/api/public/quotations',json=payload(pid),headers={'Idempotency-Key':key})
        assert created.status_code==201,created.get_json()
        reference=created.get_json()['reference']
        assert client.get('/api/v2/quotations',headers=auth('admin')).status_code==200
        assert client.patch(f'/api/v2/quotations/{reference}/status',headers=auth('admin'),json={'status':'Closed'}).status_code==403
        changed=client.patch(f'/api/v2/quotations/{reference}/status',headers=auth('subadmin'),json={'status':'In Review'})
        assert changed.status_code==200,changed.get_json()
        assert test_db.quotation_events.count_documents({'reference':reference})==1
    finally:
        test_db.quotations.delete_many({'idempotency_key':key})
        test_db.quotation_events.delete_many({'reference':locals().get('reference','')})
        test_db.inventory_batches.delete_many({'product_id':pid})
        test_db.products.delete_many({'id':pid})
