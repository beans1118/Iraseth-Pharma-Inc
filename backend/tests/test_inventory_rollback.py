"""Known gap: a failed audit insert must not leave a changed stock balance."""
from unittest.mock import patch
import pytest


@pytest.mark.xfail(strict=True, reason="Phase 1 manual release writes stock before audit log without a transaction")
def test_release_rollback_when_audit_write_fails(client, auth, test_db, product_factory):
    pid = product_factory(quantity=10)
    headers = auth("superadmin")

    import routes.inventory as inventory_module

    # Patch the collection method only during this request; restoring it is automatic.
    with patch.object(inventory_module.db.inventory_logs, "insert_one", side_effect=RuntimeError("simulated audit failure")):
        try:
            client.post(f"/api/inventory/{pid}/release", json={"qty": 3}, headers=headers)
        except RuntimeError:
            pass  # Flask TESTING mode propagates the deliberately injected error.

    assert test_db.products.find_one({"id": pid})["quantity"] == 10, (
        "Stock changed even though its required audit record failed"
    )
