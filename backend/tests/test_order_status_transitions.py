"""Known gap: a fulfilled order must never be reopened for re-deduction."""
import uuid
from datetime import datetime, timezone
import pytest


@pytest.mark.xfail(strict=True, reason="Current order PATCH allows reverting Fulfilled to Processing")
def test_fulfilled_order_cannot_be_reopened(client, auth, test_db, product_factory, monkeypatch):
    import routes.orders as orders
    monkeypatch.setattr(orders, "order_status_email", lambda *a, **k: None)
    pid = product_factory(quantity=10)
    oid = "PYTEST-ORDER-" + uuid.uuid4().hex
    test_db.orders.insert_one({
        "id": oid, "client": "Test Client", "email": "pytest@example.invalid",
        "facility": "Test Facility", "lines": [{"id": pid, "qty": 3}],
        "status": "Pending", "notes": [], "total": 0,
        "date": datetime.now(timezone.utc).isoformat(),
    })
    try:
        headers = auth("superadmin")
        url = f"/api/orders/{oid}"
        first = client.patch(url, json={"status": "Fulfilled"}, headers=headers)
        assert first.status_code == 200
        reopen = client.patch(url, json={"status": "Processing"}, headers=headers)
        assert reopen.status_code in (400, 409), (
            "Fulfilled order was reopened; it could be deducted again"
        )
        assert test_db.orders.find_one({"id": oid})["status"] == "Fulfilled"
        assert test_db.products.find_one({"id": pid})["quantity"] == 7
    finally:
        assert test_db.name == "iraseth_test"
        test_db.orders.delete_one({"id": oid})
        test_db.inventory_logs.delete_many({"note": f"Order {oid} fulfilled"})
