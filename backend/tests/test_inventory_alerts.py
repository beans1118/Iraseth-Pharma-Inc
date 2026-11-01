from modules.alerts.routes import compute_watchlist

def test_inventory_alerts_requires_auth(client):
    assert client.get('/api/v2/alerts/inventory').status_code in (401,403)

def test_inventory_alerts_validates_window(client, auth):
    assert client.get('/api/v2/alerts/inventory?days=400',headers=auth()).status_code == 400

def test_inventory_alerts_response(client, auth):
    r=client.get('/api/v2/alerts/inventory?days=30&threshold=10',headers=auth())
    assert r.status_code==200,r.get_json()
    assert isinstance(r.get_json()['stockouts'],list)

def test_watchlist_filters_ineligible_stock():
    p=[{'id':'A','name':'A','unit':'Box'}, {'id':'B','name':'B','unit':'Box'}]
    b=[{'id':'1','product_id':'A','lot':'X','expires_on':'2026-11-15','on_hand':15,'reserved':3,'condition':'available'},
       {'id':'2','product_id':'B','lot':'Y','expires_on':'2026-10-01','on_hand':60,'reserved':0,'condition':'available'}]
    result=compute_watchlist(p,b,'2026-11-01',30,15)
    assert [x['product_id'] for x in result['low_stock']]==['A']
    assert [x['product_id'] for x in result['stockouts']]==['B']
    assert len(result['expiring_batches'])==1
    assert len(result['expired_batches'])==1
