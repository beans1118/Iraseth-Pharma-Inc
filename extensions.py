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
    db.products.create_index("cat")
    db.orders.create_index("id", unique=True)
    db.orders.create_index("status")
    db.orders.create_index("email")
    db.admins.create_index("email", unique=True)
