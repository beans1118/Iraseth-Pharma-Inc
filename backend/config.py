"""
Central place that reads every setting from environment variables (via .env).
Nothing else in the app should call os.environ directly — import Config instead.
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


class Config:
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "iraseth_pharma")

    # Auth
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "8"))

    # CORS
    CORS_ORIGINS = _list(os.getenv("CORS_ORIGINS", "*"))

    # Roles (do not hardcode these anywhere else — import from here)
    ROLE_SUPERADMIN = "superadmin"
    ROLE_ADMIN = "admin"
    ROLE_SUBADMIN = "subadmin"
    ROLES = [ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_SUBADMIN]

    # Seed users (only used by seed.py). No real data — placeholders to log
    # in with on day one; change every password before going live.
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
    BACKUP_RETENTION = int(os.getenv("BACKUP_RETENTION", "30"))

    # Email
    SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "Iraseth Pharma <no-reply@irasethpharma.com>")
    SMTP_USE_TLS = _bool(os.getenv("SMTP_USE_TLS"), True)

    # App
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = _bool(os.getenv("FLASK_DEBUG"), False)
