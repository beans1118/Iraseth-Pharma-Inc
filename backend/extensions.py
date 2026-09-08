"""
Shared MongoDB connection. Import `db` anywhere you need a collection:
    from extensions import db
    db.products.find(...)
"""
from pymongo import MongoClient
from config import Config

_client = MongoClient(Config.MONGO_URI)
db = _client[Config.MONGO_DB_NAME]


def ensure_indexes():
    """Call once on startup. Safe to call repeatedly — Mongo no-ops if the index exists."""
    db.products.create_index("id", unique=True)
    db.products.create_index("category")

    db.orders.create_index("id", unique=True)
    db.orders.create_index("status")
    db.orders.create_index("email")

    # Staff accounts (superadmin / admin / subadmin). Renamed from the old
    # "admins" collection now that there's more than one role.
    db.users.create_index("email", unique=True)
    db.users.create_index("role")

    # One doc per login. jti ties it back to the JWT so /auth/logout can
    # find "the session that belongs to this token" without any server-side
    # session store.
    db.sessions.create_index("jti", unique=True)
    db.sessions.create_index("user_email")
    db.sessions.create_index("login_at")

    # One doc per stock change (release or supply add), plus who did it.
    db.inventory_logs.create_index("product_id")
    db.inventory_logs.create_index("at")
    db.inventory_logs.create_index("actor_email")

    db.backups.create_index("created_at")
