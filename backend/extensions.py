"""
Shared MongoDB connection. Import `db` anywhere you need a collection:
    from extensions import db
    db.products.find(...)
"""
from pymongo import ASCENDING, DESCENDING, MongoClient
from config import Config

_client = MongoClient(
    Config.MONGO_URI,
    maxPoolSize=Config.MONGO_MAX_POOL_SIZE,
    minPoolSize=Config.MONGO_MIN_POOL_SIZE,
    serverSelectionTimeoutMS=Config.MONGO_SERVER_SELECTION_TIMEOUT_MS,
    connectTimeoutMS=Config.MONGO_CONNECT_TIMEOUT_MS,
    socketTimeoutMS=Config.MONGO_SOCKET_TIMEOUT_MS,
)
db = _client[Config.MONGO_DB_NAME]


def ensure_indexes():
    """Call once on startup. Safe to call repeatedly."""
    db.invoices.create_index("id", unique=True)
    db.invoices.create_index([("actor_email", 1), ("idempotency_key", 1)], unique=True)
    db.invoices.create_index("created_at")
    db.invoice_events.create_index("id", unique=True)
    db.invoice_events.create_index([("invoice_id", 1), ("at", -1)])
    # Order-support OTPs, temporary customer sessions and chat history.
    db.support_challenges.create_index('id', unique=True)
    db.support_challenges.create_index('expires_at', expireAfterSeconds=0)
    db.support_challenges.create_index([('order_id', 1), ('email', 1), ('expires_at', -1)])
    db.support_sessions.create_index('token_hash', unique=True)
    db.support_sessions.create_index('expires_at', expireAfterSeconds=0)
    db.support_messages.create_index('id', unique=True)
    db.support_messages.create_index([('order_id', 1), ('at', -1)])
    db.support_threads.create_index('order_id', unique=True)
    db.support_threads.create_index('updated_at')
    db.support_rate_limits.create_index('expires_at', expireAfterSeconds=0)
    # Batch-mode indexes (created even while feature is disabled).
    db.inventory_batches.create_index('id', unique=True)
    db.inventory_batches.create_index([('product_id', 1), ('lot', 1),
        ('expires_on', 1), ('condition', 1), ('unverified', 1)], unique=True)
    db.inventory_batches.create_index([('product_id', 1), ('condition', 1), ('expires_on', 1)])
    db.stock_movements.create_index('id', unique=True)
    db.stock_movements.create_index([('product_id', 1), ('at', -1)])
    db.inventory_operations.create_index('key', unique=True)
    db.stock_reservations.create_index('id', unique=True)
    db.stock_reservations.create_index([('order_id', 1), ('status', 1)])
    db.inventory_adjustments.create_index('id', unique=True)
    db.inventory_adjustments.create_index([('status', 1), ('requested_at', -1)])
    db.products.create_index("id", unique=True)
    db.products.create_index("category")

    db.orders.create_index("id", unique=True)
    db.orders.create_index("status")
    db.orders.create_index("email")
    db.orders.create_index([("status", ASCENDING), ("date", DESCENDING)])

    # Staff accounts (superadmin / admin / subadmin).
    db.users.create_index("email", unique=True)
    db.users.create_index("role")

    # One doc per login. jti ties it back to the JWT.
    db.sessions.create_index("jti", unique=True)
    db.sessions.create_index("user_email")
    db.sessions.create_index("login_at")
    db.sessions.create_index([("user_email", ASCENDING), ("login_at", DESCENDING)])
    db.sessions.create_index([("role", ASCENDING), ("login_at", DESCENDING)])

    # One doc per stock change (release/supply/opening), plus who did it.
    db.inventory_logs.create_index("product_id")
    db.inventory_logs.create_index("at")
    db.inventory_logs.create_index("actor_email")
    db.inventory_logs.create_index("month")
    db.inventory_logs.create_index([("product_id", ASCENDING), ("at", DESCENDING)])
    db.inventory_logs.create_index([("action", ASCENDING), ("at", DESCENDING)])

    # Exactly one beginning-stock snapshot per product per month.
    # The partial index applies only to monthly_opening rows, so ordinary
    # release/supply rows are unaffected.
    db.inventory_logs.create_index(
        [("month", ASCENDING), ("product_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"action": "monthly_opening"},
        name="uniq_monthly_opening_per_product",
    )

    db.backups.create_index("created_at")

    # Distributed fixed-window rate-limit buckets. MongoDB automatically
    # removes expired buckets after their window is no longer useful.
    db.rate_limits.create_index("expires_at", expireAfterSeconds=0)
