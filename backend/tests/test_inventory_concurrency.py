"""Two simultaneous API releases must not overdraw one product."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


def test_simultaneous_release_never_overdraws(client, auth, test_db, product_factory):
    product_id = product_factory(quantity=5)
    headers = auth("superadmin")
    barrier = Barrier(2)

    def release():
        # Flask's test client should not be shared across threads.
        with client.application.test_client() as separate_client:
            barrier.wait(timeout=10)
            response = separate_client.post(
                f"/api/inventory/{product_id}/release",
                json={"qty": 4, "note": "Concurrent test"},
                headers=headers,
            )
            return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: release(), range(2)))

    assert sorted(statuses) == [200, 400], statuses
    assert test_db.products.find_one({"id": product_id})["quantity"] == 1
    assert test_db.inventory_logs.count_documents(
        {"product_id": product_id, "action": "release"}
    ) == 1
