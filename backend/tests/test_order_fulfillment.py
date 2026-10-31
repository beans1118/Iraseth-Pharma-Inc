"""Transactional fulfillment: one deduction; all lines roll back on shortage."""
import uuid
from datetime import datetime, timezone

import pytest


@pytest.fixture
def create_test_order(test_db):
    ids = []

    def make(lines):
        order_id = "PYTEST-ORDER-" + uuid.uuid4().hex
        test_db.orders.insert_one({
            "id": order_id,
            "client": "Test Client",
            "email": "pytest@example.invalid",
            "facility": "Test Facility",
            "lines": [{"id": pid, "qty": qty} for pid, qty in lines],
            "status": "Pending",
            "notes": [],
            "date": datetime.now(timezone.utc).isoformat(),
            "total": 0,
        })
        ids.append(order_id)
        return order_id

    try:
        yield make
    finally:
        assert test_db.name == "iraseth_test"
        test_db.orders.delete_many({"id": {"$in": ids}})
        test_db.inventory_logs.delete_many({"note": {"$in": [f"Order {oid} fulfilled" for oid in ids]}})


def test_fulfillment_deducts_only_once(client, auth, test_db, product_factory, create_test_order, monkeypatch):
    import routes.orders as orders
    monkeypatch.setattr(orders, "order_status_email", lambda *a, **k: None)
    pid = product_factory(quantity=10)
    oid = create_test_order([(pid, 4)])
    headers = auth("superadmin")
    url = f"/api/orders/{oid}"

    first = client.patch(url, json={"status": "Fulfilled"}, headers=headers)
    second = client.patch(url, json={"status": "Fulfilled"}, headers=headers)
    assert first.status_code == 200, first.get_json()
    assert second.status_code in (200, 400, 409), second.get_json()
    assert test_db.products.find_one({"id": pid})["quantity"] == 6
    assert test_db.orders.find_one({"id": oid})["status"] == "Fulfilled"
    assert test_db.inventory_logs.count_documents({"product_id": pid, "note": f"Order {oid} fulfilled"}) == 1


def test_multi_item_shortage_rolls_back_everything(client, auth, test_db, product_factory, create_test_order, monkeypatch):
    import routes.orders as orders
    monkeypatch.setattr(orders, "order_status_email", lambda *a, **k: None)
    first_pid = product_factory(quantity=10)
    second_pid = product_factory(quantity=1)
    oid = create_test_order([(first_pid, 4), (second_pid, 5)])

    response = client.patch(f"/api/orders/{oid}", json={"status": "Fulfilled"}, headers=auth("superadmin"))
    assert response.status_code == 409, response.get_json()
    assert test_db.products.find_one({"id": first_pid})["quantity"] == 10
    assert test_db.products.find_one({"id": second_pid})["quantity"] == 1
    assert test_db.orders.find_one({"id": oid})["status"] == "Pending"
    assert test_db.inventory_logs.count_documents({"note": f"Order {oid} fulfilled"}) == 0
