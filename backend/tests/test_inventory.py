def test_release_rejects_insufficient_stock(client, auth, test_db, product_factory):
    pid = product_factory(quantity=3)
    h = auth('superadmin')
    r = client.post(f'/api/inventory/{pid}/release', headers=h, json={'qty':4})
    assert r.status_code == 400
    assert test_db.products.find_one({'id':pid})['quantity'] == 3


def test_supply_and_release_create_logs(client, auth, test_db, product_factory):
    pid = product_factory(quantity=10)
    h = auth('superadmin')
    assert client.post(f'/api/inventory/{pid}/supply', headers=h, json={'qty':5}).status_code == 200
    assert test_db.products.find_one({'id':pid})['quantity'] == 15
    assert client.post(f'/api/inventory/{pid}/release', headers=h, json={'qty':4}).status_code == 200
    assert test_db.products.find_one({'id':pid})['quantity'] == 11
    assert test_db.inventory_logs.count_documents({'product_id':pid, 'action':{'$in':['supply','release']}}) == 2


def test_nonpositive_release_rejected(client, auth, product_factory):
    pid = product_factory()
    r = client.post(f'/api/inventory/{pid}/release', headers=auth(), json={'qty':0})
    assert r.status_code == 400
