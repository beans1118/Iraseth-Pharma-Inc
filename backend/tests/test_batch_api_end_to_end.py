"""Authenticated API integration tests for the opt-in batch engine.

Run with: python -m pytest tests/test_batch_api_end_to_end.py -v
Requires local MongoDB replica set and the existing tests/conftest.py.
Creates disposable records only in iraseth_test and cleans up records by exact IDs.
"""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from config import Config


def new_key():
    return f"pytest-e2e-{uuid4().hex}"


def future(days):
    return (date.today() + timedelta(days=days)).isoformat()


@pytest.fixture
def api_batch(monkeypatch, test_db, client, auth):
    assert test_db.name == "iraseth_test", "Refusing to run outside isolated test database"
    monkeypatch.setattr(Config, "BATCH_MODE", True)
    pid = "E2E-" + uuid4().hex
    test_db.products.insert_one({
        "id": pid, "name": "API E2E sample", "quantity": 0,
        "baseline_qty": 0, "unit": "pcs", "category": "testing", "price": 1,
    })
    orders = []
    operation_keys = []

    def headers(role="superadmin"):
        return {**auth(role), "Idempotency-Key": new_key()}

    def post(url, payload=None, role="superadmin"):
        h = headers(role)
        operation_keys.append(h["Idempotency-Key"])
        return client.post(url, json=payload or {}, headers=h)

    def order(qty):
        oid = "E2E-ORDER-" + uuid4().hex
        test_db.orders.insert_one({"id": oid, "status": "Pending", "lines": [{"id": pid, "qty": qty}]})
        orders.append(oid)
        return oid

    try:
        yield {"pid": pid, "post": post, "order": order, "headers": headers, "client": client, "db": test_db}
    finally:
        # Clean only records created by this fixture.
        test_db.stock_reservations.delete_many({"order_id": {"$in": orders}})
        test_db.orders.delete_many({"id": {"$in": orders}})
        batch_ids = [b["id"] for b in test_db.inventory_batches.find({"product_id": pid}, {"id": 1})]
        test_db.inventory_adjustments.delete_many({"batch_id": {"$in": batch_ids}})
        test_db.stock_movements.delete_many({"product_id": pid})
        test_db.inventory_batches.delete_many({"product_id": pid})
        test_db.inventory_operations.delete_many({"key": {"$in": operation_keys}})
        test_db.products.delete_one({"id": pid})


def check_response(response, status):
    assert response.status_code == status, (response.status_code, response.get_json())
    return response.get_json()


def test_authenticated_receipt_fefo_and_audit(api_batch):
    pid, post, db = api_batch["pid"], api_batch["post"], api_batch["db"]
    later = check_response(post("/api/v2/inventory/batches/receive", {
        "product_id": pid, "lot": "LATE", "expires_on": future(80), "qty": 8,
    }), 201)
    early = check_response(post("/api/v2/inventory/batches/receive", {
        "product_id": pid, "lot": "EARLY", "expires_on": future(20), "qty": 5,
    }), 201)
    result = check_response(post("/api/v2/inventory/release", {
        "product_id": pid, "qty": 7, "reason": "API FEFO check",
    }), 200)
    assert [(x["batch_id"], x["qty"]) for x in result["allocations"]] == [
        (early["id"], 5), (later["id"], 2)
    ]
    assert db.products.find_one({"id": pid})["quantity"] == 6
    assert db.inventory_batches.find_one({"id": early["id"]})["on_hand"] == 0
    assert db.stock_movements.count_documents({"product_id": pid}) >= 3


def test_approve_fulfill_and_prevent_double_deduction(api_batch):
    pid, post, db = api_batch["pid"], api_batch["post"], api_batch["db"]
    batch = check_response(post("/api/v2/inventory/batches/receive", {
        "product_id": pid, "lot": "ORDER", "expires_on": future(90), "qty": 12,
    }), 201)
    oid = api_batch["order"](5)
    approved = check_response(post(f"/api/v2/orders/{oid}/approve"), 200)
    assert approved["status"] == "Approved"
    assert db.inventory_batches.find_one({"id": batch["id"]})["reserved"] == 5
    fulfilled = check_response(post(f"/api/v2/orders/{oid}/fulfill"), 200)
    assert fulfilled["status"] == "Fulfilled"
    assert db.products.find_one({"id": pid})["quantity"] == 7
    assert db.inventory_batches.find_one({"id": batch["id"]})["reserved"] == 0
    repeat = post(f"/api/v2/orders/{oid}/fulfill")
    assert repeat.status_code in (400, 409), (repeat.status_code, repeat.get_json())
    assert db.products.find_one({"id": pid})["quantity"] == 7


def test_cancel_order_restores_available_stock(api_batch):
    pid, post, db = api_batch["pid"], api_batch["post"], api_batch["db"]
    batch = check_response(post("/api/v2/inventory/batches/receive", {
        "product_id": pid, "lot": "CANCEL", "expires_on": future(60), "qty": 9,
    }), 201)
    oid = api_batch["order"](6)
    check_response(post(f"/api/v2/orders/{oid}/approve"), 200)
    check_response(post(f"/api/v2/orders/{oid}/cancel"), 200)
    assert db.orders.find_one({"id": oid})["status"] == "Cancelled"
    assert db.inventory_batches.find_one({"id": batch["id"]})["reserved"] == 0
    assert db.products.find_one({"id": pid})["quantity"] == 9


def test_adjustments_are_role_separated_and_approved(api_batch):
    pid, post, db = api_batch["pid"], api_batch["post"], api_batch["db"]
    batch = check_response(post("/api/v2/inventory/batches/receive", {
        "product_id": pid, "lot": "COUNT", "expires_on": future(45), "qty": 8,
    }), 201)
    request_data = {"batch_id": batch["id"], "delta": -2, "reason": "Cycle count discrepancy"}
    denied = post("/api/v2/inventory/adjustments", request_data, "superadmin")
    assert denied.status_code == 403, (denied.status_code, denied.get_json())
    adjustment = check_response(post("/api/v2/inventory/adjustments", request_data, "subadmin"), 201)
    assert db.products.find_one({"id": pid})["quantity"] == 8
    decision_url = f"/api/v2/inventory/adjustments/{adjustment['id']}/decision"
    denied = post(decision_url, {"approve": True}, "subadmin")
    assert denied.status_code == 403, (denied.status_code, denied.get_json())
    approved = check_response(post(decision_url, {"approve": True}), 200)
    assert approved["status"] == "approved"
    assert db.products.find_one({"id": pid})["quantity"] == 6
