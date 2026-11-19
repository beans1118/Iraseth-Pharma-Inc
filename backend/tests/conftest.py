"""Load and lock test settings before application/database imports."""
import os

os.environ["BATCH_MODE"] = "false"
import uuid
from pathlib import Path

import pytest
from utils.test_configuration import local_test_settings

BACKEND = Path(__file__).resolve().parents[1]
settings, SAFE_URI, SAFE_PORT = local_test_settings(BACKEND)

for key, value in settings.items():
    if value is not None:
        os.environ[key] = value
# Critical runtime settings are forced for the *test process*.
os.environ.update(APP_ENV="testing", MONGO_DB_NAME="iraseth_test", MONGO_URI=SAFE_URI,
                  RATE_LIMIT_LOGIN_PER_MINUTE="10000", RATE_LIMIT_INVENTORY_WRITES_PER_MINUTE="10000",
                  RATE_LIMIT_PUBLIC_ORDERS_PER_MINUTE="10000")

from app import app as flask_app  # noqa: E402
from extensions import db  # noqa: E402
from utils.security import hash_password  # noqa: E402


def assert_safe_database():
    assert os.environ["APP_ENV"] == "testing"
    assert db.name == "iraseth_test"
    # Verify the actual MongoClient endpoint too, not just .env contents.
    assert db.client.address == ("127.0.0.1", SAFE_PORT)


@pytest.fixture
def client():
    assert_safe_database()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def test_db():
    assert_safe_database()
    return db


@pytest.fixture
def accounts(test_db):
    """Disposable staff accounts; cleanup only documents belonging to this fixture."""
    marker = uuid.uuid4().hex
    users = {}
    for role in ("superadmin", "admin", "subadmin"):
        email = f"pytest-{role}-{marker}@example.invalid"
        password = f"LocalTest-{marker}!"
        test_db.users.insert_one({"email": email, "name": f"Test {role}", "role": role,
                                  "password_hash": hash_password(password)})
        users[role] = {"email": email, "password": password, "role": role}
    try:
        yield users
    finally:
        assert_safe_database()
        emails = [u["email"] for u in users.values()]
        test_db.sessions.delete_many({"user_email": {"$in": emails}})
        test_db.users.delete_many({"email": {"$in": emails}})


@pytest.fixture
def auth(client, accounts):
    def make_headers(role="superadmin"):
        account = accounts[role]
        response = client.post("/api/auth/login", json={"email": account["email"], "password": account["password"]})
        assert response.status_code == 200, response.get_json()
        return {"Authorization": f"Bearer {response.get_json()['token']}"}
    return make_headers


@pytest.fixture
def product_factory(test_db):
    """Create disposable catalog items; delete only the exact generated IDs."""
    created = []

    def make(quantity=10, price=4.5):
        pid = "PYTEST-" + uuid.uuid4().hex
        doc = {"id": pid, "name": "Pytest Sample", "description": "Automated test item",
               "category": "testing", "unit": "pcs", "quantity": quantity,
               "baseline_qty": quantity, "price": price}
        test_db.products.insert_one(doc)
        created.append(pid)
        return pid

    try:
        yield make
    finally:
        assert_safe_database()
        test_db.inventory_logs.delete_many({"product_id": {"$in": created}})
        test_db.products.delete_many({"id": {"$in": created}})
