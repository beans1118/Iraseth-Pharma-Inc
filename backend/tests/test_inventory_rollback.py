"""A failed audit insert must roll back the associated stock change."""

from unittest.mock import patch

import pytest


def test_release_rollback_when_audit_write_fails(client, auth, test_db, product_factory):
    pid = product_factory(quantity=10)
    headers = auth("superadmin")

    # Patch PyMongo's Collection class, not a temporary collection instance.
    with patch(
        "pymongo.collection.Collection.insert_one",
        side_effect=RuntimeError("simulated audit failure"),
    ) as mocked_insert:
        with pytest.raises(RuntimeError, match="simulated audit failure"):
            client.post(
                f"/api/inventory/{pid}/release",
                json={"qty": 3},
                headers=headers,
            )
        mocked_insert.assert_called()

    assert test_db.inventory_logs.count_documents(
        {"product_id": pid, "action": "release"}
    ) == 0
    assert test_db.products.find_one({"id": pid})["quantity"] == 10, (
        "Stock changed even though its required audit record failed"
    )


def test_supply_rollback_when_audit_write_fails(client, auth, test_db, product_factory):
    pid = product_factory(quantity=10)
    headers = auth("superadmin")

    with patch(
        "pymongo.collection.Collection.insert_one",
        side_effect=RuntimeError("simulated audit failure"),
    ) as mocked_insert:
        with pytest.raises(RuntimeError, match="simulated audit failure"):
            client.post(
                f"/api/inventory/{pid}/supply",
                json={"qty": 3},
                headers=headers,
            )
        mocked_insert.assert_called()

    assert test_db.products.find_one({"id": pid})["quantity"] == 10
    assert test_db.inventory_logs.count_documents(
        {"product_id": pid, "action": "supply"}
    ) == 0
