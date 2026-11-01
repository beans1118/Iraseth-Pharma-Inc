"""Invoice tests run only with conftest's isolated iraseth_test database."""
import uuid

def test_invoice_lifecycle(client, auth, test_db, product_factory):
    product_id=product_factory(quantity=4,price=10)
    headers={**auth('superadmin'),'Idempotency-Key':'TEST-'+uuid.uuid4().hex}
    body={'client':'Test Pharmacy','email':'invoice-test@example.invalid','facility':'Test Clinic',
          'lines':[{'id':product_id,'qty':2,'price':'25.50'}]}
    invoice_id=None
    try:
        response=client.post('/api/v2/invoices',json=body,headers=headers)
        assert response.status_code==201,response.get_json()
        invoice=response.get_json();invoice_id=invoice['id']
        assert invoice['total']=='51.00'
        assert invoice['status']=='Draft'
        # Idempotent replay, no second invoice or event.
        replay=client.post('/api/v2/invoices',json=body,headers=headers)
        assert replay.status_code==200
        assert replay.get_json()['id']==invoice_id
        assert test_db.invoices.count_documents({'id':invoice_id})==1
        assert test_db.invoice_events.count_documents({'invoice_id':invoice_id})==1
        # Invoice operations never deduct catalog stock.
        assert test_db.products.find_one({'id':product_id})['quantity']==4
        issued=client.post(f'/api/v2/invoices/{invoice_id}/issue',headers=headers)
        assert issued.status_code==200
        assert issued.get_json()['status']=='Issued'
        assert client.post(f'/api/v2/invoices/{invoice_id}/issue',headers=headers).status_code==409
        assert client.get('/api/v2/invoices/transactions',headers=headers).status_code==200
        voided=client.post(f'/api/v2/invoices/{invoice_id}/void',headers=headers)
        assert voided.status_code==200
        assert voided.get_json()['status']=='Voided'
        assert test_db.products.find_one({'id':product_id})['quantity']==4
        assert test_db.invoice_events.count_documents({'invoice_id':invoice_id})==3
    finally:
        if invoice_id:
            test_db.invoice_events.delete_many({'invoice_id':invoice_id})
            test_db.invoices.delete_many({'id':invoice_id})

def test_invoice_requires_auth_and_valid_price(client, auth, test_db, product_factory):
    pid=product_factory()
    key='TEST-'+uuid.uuid4().hex
    body={'client':'Test Pharmacy','email':'test@example.invalid','facility':'Test',
          'lines':[{'id':pid,'qty':1,'price':'-4.00'}]}
    assert client.post('/api/v2/invoices',json=body,headers={'Idempotency-Key':key}).status_code==401
    assert client.post('/api/v2/invoices',json=body,headers={**auth(), 'Idempotency-Key':key}).status_code==400
    assert test_db.invoices.count_documents({'idempotency_key':key})==0
