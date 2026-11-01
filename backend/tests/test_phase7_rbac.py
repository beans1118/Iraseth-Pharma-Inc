"""Phase 7 authorization regression tests. Uses isolated iraseth_test fixtures."""


def test_subadmin_can_create_and_edit_catalog_product(client, auth, test_db):
    import uuid
    pid = "PYTEST-RBAC-" + uuid.uuid4().hex
    headers = auth("subadmin")
    doc = dict(id=pid, name="RBAC Test", description="", category="testing", unit="pcs", quantity=0)
    try:
        created = client.post("/api/products", headers=headers, json=doc)
        assert created.status_code == 201, created.get_json()
        modified = client.put(f"/api/products/{pid}", headers=headers, json={"name": "Updated"})
        assert modified.status_code == 200, modified.get_json()
        forbidden = client.delete(f"/api/products/{pid}", headers=headers)
        assert forbidden.status_code == 403
    finally:
        test_db.products.delete_many({"id": pid})


def test_board_admin_cannot_modify_catalog(client, auth):
    headers = auth("admin")
    doc = dict(id="BOARD-TEST", name="No write", description="", category="testing", unit="pcs", quantity=0)
    assert client.post("/api/products", headers=headers, json=doc).status_code == 403
    assert client.put("/api/products/BOARD-TEST", headers=headers, json={"name":"No"}).status_code == 403
    assert client.delete("/api/products/BOARD-TEST", headers=headers).status_code == 403


def test_board_admin_cannot_write_invoices_or_support(client, auth):
    headers = auth("admin")
    assert client.post("/api/v2/invoices", headers=headers, json={}).status_code == 403
    assert client.post("/api/v2/invoices/test/issue", headers=headers).status_code == 403
    assert client.post("/api/v2/invoices/test/void", headers=headers).status_code == 403
    assert client.post("/api/v2/support/staff/threads", headers=headers, json={}).status_code == 403
    assert client.post("/api/v2/support/staff/threads/test/messages", headers=headers, json={}).status_code == 403
