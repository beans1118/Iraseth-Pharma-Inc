"""
Central application configuration.
All runtime settings are read from environment variables so production secrets
and deployment-specific values do not need to live in source control.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _list(value):
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _int(value, default, minimum=0):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)


class Config:
    # Environment
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    IS_PRODUCTION = APP_ENV == "production"

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "iraseth_pharma")
    MONGO_MAX_POOL_SIZE = _int(os.getenv("MONGO_MAX_POOL_SIZE"), 50, 1)
    MONGO_MIN_POOL_SIZE = _int(os.getenv("MONGO_MIN_POOL_SIZE"), 0, 0)
    MONGO_SERVER_SELECTION_TIMEOUT_MS = _int(
        os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS"), 5000, 1000
    )
    MONGO_CONNECT_TIMEOUT_MS = _int(
        os.getenv("MONGO_CONNECT_TIMEOUT_MS"), 5000, 1000
    )
    MONGO_SOCKET_TIMEOUT_MS = _int(
        os.getenv("MONGO_SOCKET_TIMEOUT_MS"), 20000, 1000
    )

    # Auth
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_EXPIRES_HOURS = _int(os.getenv("JWT_EXPIRES_HOURS"), 8, 1)

    # CORS / Socket.IO
    CORS_ORIGINS = _list(os.getenv("CORS_ORIGINS", "*"))
    SOCKET_AUTH_REQUIRED = _bool(
        os.getenv("SOCKET_AUTH_REQUIRED"),
        IS_PRODUCTION,
    )

    # Trusted reverse proxies. Local development should leave this at 0.
    # Render normally uses one trusted proxy hop. If Cloudflare is later added
    # in front, review this value against the final proxy chain before launch.
    TRUST_PROXY_COUNT = _int(os.getenv("TRUST_PROXY_COUNT"), 0, 0)

    # Fixed-window API rate limits. These are enforced through MongoDB so the
    # counters work even if the backend later runs more than one process.
    RATE_LIMIT_LOGIN_PER_MINUTE = _int(
        os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE"), 10, 1
    )
    RATE_LIMIT_PUBLIC_ORDERS_PER_MINUTE = _int(
        os.getenv("RATE_LIMIT_PUBLIC_ORDERS_PER_MINUTE"), 30, 1
    )
    RATE_LIMIT_INVENTORY_WRITES_PER_MINUTE = _int(
        os.getenv("RATE_LIMIT_INVENTORY_WRITES_PER_MINUTE"), 120, 1
    )
    RATE_LIMIT_BACKUP_PER_MINUTE = _int(
        os.getenv("RATE_LIMIT_BACKUP_PER_MINUTE"), 5, 1
    )

    # Roles
    ROLE_SUPERADMIN = "superadmin"
    ROLE_ADMIN = "admin"
    ROLE_SUBADMIN = "subadmin"
    ROLES = [ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_SUBADMIN]

    # Seed users. Change every default before production.
    SEED_USERS = [
        {
            "email": os.getenv("SEED_SUPERADMIN_EMAIL", "superadmin@irasethpharma.com"),
            "password": os.getenv("SEED_SUPERADMIN_PASSWORD", "change-me-superadmin"),
            "name": os.getenv("SEED_SUPERADMIN_NAME", "Super Admin"),
            "role": ROLE_SUPERADMIN,
        },
        {
            "email": os.getenv("SEED_ADMIN_EMAIL", "admin@irasethpharma.com"),
            "password": os.getenv("SEED_ADMIN_PASSWORD", "change-me-admin"),
            "name": os.getenv("SEED_ADMIN_NAME", "Admin"),
            "role": ROLE_ADMIN,
        },
        {
            "email": os.getenv("SEED_SUBADMIN_EMAIL", "subadmin@irasethpharma.com"),
            "password": os.getenv("SEED_SUBADMIN_PASSWORD", "change-me-subadmin"),
            "name": os.getenv("SEED_SUBADMIN_NAME", "Sub Admin"),
            "role": ROLE_SUBADMIN,
        },
    ]

    # Backups
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
    BACKUP_RETENTION = _int(os.getenv("BACKUP_RETENTION"), 30, 1)

    # Email
    SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT = _int(os.getenv("SMTP_PORT"), 587, 1)
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "Iraseth Pharma <no-reply@irasethpharma.com>")
    SMTP_USE_TLS = _bool(os.getenv("SMTP_USE_TLS"), True)
    SMTP_TIMEOUT_SECONDS = _int(os.getenv("SMTP_TIMEOUT_SECONDS"), 5, 1)
    EMAIL_ASYNC = _bool(os.getenv("EMAIL_ASYNC"), True)
    EMAIL_WORKERS = _int(os.getenv("EMAIL_WORKERS"), 2, 1)

    # Performance
    MAX_ORDER_LINES = _int(os.getenv("MAX_ORDER_LINES"), 100, 1)
    API_MAX_PAGE_SIZE = _int(os.getenv("API_MAX_PAGE_SIZE"), 200, 1)
    COMPRESS_MIN_SIZE = _int(os.getenv("COMPRESS_MIN_SIZE"), 1024, 0)

    # App
    FLASK_PORT = _int(os.getenv("FLASK_PORT"), 5000, 1)
    FLASK_DEBUG = _bool(os.getenv("FLASK_DEBUG"), False)

    @classmethod
    def validate_production(cls):
        """Fail fast when unsafe development defaults reach production."""
        if not cls.IS_PRODUCTION:
            return

        problems = []

        weak_jwt_values = {
            "",
            "dev-secret-change-me",
            "change-this-to-a-long-random-string",
        }
        if cls.JWT_SECRET in weak_jwt_values or len(cls.JWT_SECRET) < 32:
            problems.append("JWT_SECRET must be a strong value of at least 32 characters")

        if not cls.CORS_ORIGINS or "*" in cls.CORS_ORIGINS:
            problems.append("CORS_ORIGINS must list explicit production frontend origins")

        default_passwords = {
            "change-me-superadmin",
            "change-me-admin",
            "change-me-subadmin",
        }
        if any(user["password"] in default_passwords for user in cls.SEED_USERS):
            problems.append("default seed account passwords must be changed")

        if cls.FLASK_DEBUG:
            problems.append("FLASK_DEBUG must be false in production")

        if problems:
            raise RuntimeError(
                "Unsafe production configuration: " + "; ".join(problems)
            )
