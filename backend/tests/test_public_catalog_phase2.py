"""Phase 2 public storefront catalog regression tests.

Runs with the established iraseth_test isolated MongoDB fixture; no seed/reset.
"""
from datetime import date, timedelta
from uuid import uuid4

from config import Config


def _pid():
    return "PYTEST-PUBLIC-" + uuid4().hex


def test_new_product_publishes_by_default_with_no_price_or_stock(client, auth, test_db):
    pid = _pid()
    try:
        response = client.post("/api/products", headers=auth("subadmin"), json={
            "id": pid, "name": "Public API Product", "category": "Medical Devices",
            "unit": "pcs", "description": "Product description", "quantity": 0,
        })
        assert response.status_code == 201, response.get_json()
        stored = test_db.products.find_one({"id": pid})
        assert stored["storefront_visible"] is True
        assert stored["storefront_price"] is None
        public = client.get(f"/api/public/products/{pid}")
        assert public.status_code == 200, public.get_json()
        product = public.get_json()
        assert product["name"] == "Public API Product"
        assert product["publicPrice"] is None
        assert product["inStock"] is False
        assert product["slug"] == pid
        assert public.headers["Cache-Control"] == "no-store"
        assert not ({"quantity", "cost", "baseline_qty", "_id", "reserved"} & product.keys())
    finally:
        test_db.products.delete_many({"id": pid})


def test_staff_price_visibility_audit_and_permissions(client, auth, test_db):
    pid = _pid()
    test_db.products.insert_one({"id": pid, "name": "Price Test", "category": "test",
                                 "price": 888.00, "quantity": 0, "storefront_visible": True})
    try:
        url = f"/api/products/{pid}/storefront"
        assert client.patch(url, headers=auth("admin"), json={"publicPrice": 199.50}).status_code == 403
        assert client.patch(url, headers=auth("subadmin"), json={"publicPrice": 199.50}).status_code == 403
        assert client.patch(url, json={"publicPrice": 199.50}).status_code == 401
        response = client.patch(url, headers=auth("superadmin"),
                                json={"visible": True, "publicPrice": 199.50})
        assert response.status_code == 200, response.get_json()
        assert response.get_json()["publicPrice"] == 199.50
        public = client.get(f"/api/public/products/{pid}")
        assert public.status_code == 200
        assert public.get_json()["publicPrice"] == 199.50
        stored = test_db.products.find_one({"id": pid})
        assert stored["price"] == 888.00  # Old internal price unaffected.
        assert test_db.catalog_events.count_documents({"product_id": pid}) == 1
        hidden = client.patch(url, headers=auth("superadmin"), json={"visible": False})
        assert hidden.status_code == 200
        assert client.get(f"/api/public/products/{pid}").status_code == 404
        listed = client.get("/api/public/products?limit=200")
        assert all(p["id"] != pid for p in listed.get_json()["products"])
    finally:
        test_db.catalog_events.delete_many({"product_id": pid})
        test_db.products.delete_many({"id": pid})


def test_price_validation_and_no_stock_side_effect(client, auth, test_db):
    pid = _pid()
    test_db.products.insert_one({"id": pid, "name": "Test", "category": "test",
                                 "quantity": 0, "storefront_visible": True})
    try:
        headers = auth("superadmin")
        for value in (-1, "nan", "Infinity", "1.999", True, "not-price"):
            bad = client.patch(f"/api/products/{pid}/storefront", headers=headers,
                               json={"publicPrice": value})
            assert bad.status_code == 400, (value, bad.get_json())
        assert test_db.catalog_events.count_documents({"product_id": pid}) == 0
        assert test_db.products.find_one({"id": pid})["quantity"] == 0
    finally:
        test_db.products.delete_many({"id": pid})


def test_available_stock_only_uses_eligible_batches(client, test_db, monkeypatch):
    pid = _pid()
    tomorrow = (date.today() + timedelta(days=3)).isoformat()
    yesterday = (date.today() - timedelta(days=3)).isoformat()
    test_db.products.insert_one({"id": pid, "name": "Batch Test", "category": "test",
                                 "quantity": 500, "storefront_visible": True})
    docs = [
        {"id": uuid4().hex, "product_id": pid, "lot": "A", "expires_on": tomorrow,
         "condition": "available", "unverified": False, "on_hand": 4, "reserved": 4},
        {"id": uuid4().hex, "product_id": pid, "lot": "B", "expires_on": yesterday,
         "condition": "available", "unverified": False, "on_hand": 5, "reserved": 0},
        {"id": uuid4().hex, "product_id": pid, "lot": "C", "expires_on": tomorrow,
         "condition": "quarantine", "unverified": False, "on_hand": 5, "reserved": 0},
        {"id": uuid4().hex, "product_id": pid, "lot": "D", "expires_on": tomorrow,
         "condition": "available", "unverified": True, "on_hand": 5, "reserved": 0},
    ]
    try:
        test_db.inventory_batches.insert_many(docs)
        monkeypatch.setattr(Config, "BATCH_MODE", True)
        assert client.get(f"/api/public/products/{pid}").get_json()["inStock"] is False
        test_db.inventory_batches.update_one({"id": docs[0]["id"]}, {"$set": {"reserved": 3}})
        assert client.get(f"/api/public/products/{pid}").get_json()["inStock"] is True
    finally:
        test_db.inventory_batches.delete_many({"id": {"$in": [d["id"] for d in docs]}})
        test_db.products.delete_many({"id": pid})


def test_existing_catalog_product_is_visible_without_public_price(client, test_db):
    """Migration-free: old product documents remain visible, not incorrectly priced."""
    pid = _pid()
    test_db.products.insert_one({"id": pid, "name": "Existing Catalog Item",
                                 "description": "Old product", "category": "test",
                                 "price": 99999, "quantity": 0})
    try:
        response = client.get(f"/api/public/products/{pid}")
        assert response.status_code == 200
        product = response.get_json()
        assert product["publicPrice"] is None
        assert product["inStock"] is False
        assert "price" not in product
    finally:
        test_db.products.delete_many({"id": pid})


def test_public_catalog_pagination_bounds(client):
    for invalid in ("page=0", "page=-1", "page=nan", "limit=0", "limit=201"):
        response = client.get("/api/public/products?" + invalid)
        assert response.status_code == 400, (invalid, response.get_json())


def test_storefront_settings_reject_unknown_fields(client, auth, test_db):
    pid = _pid()
    test_db.products.insert_one({"id": pid, "name": "Protected Item",
                                 "category": "test", "quantity": 0})
    try:
        url = f"/api/products/{pid}/storefront"
        headers = auth("superadmin")
        response = client.patch(url, headers=headers,
                                json={"visible": True, "quantity": 10000})
        assert response.status_code == 400
        assert test_db.products.find_one({"id": pid})["quantity"] == 0
        assert test_db.catalog_events.count_documents({"product_id": pid}) == 0
    finally:
        test_db.products.delete_many({"id": pid})
