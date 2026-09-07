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

    # Seed admin (only used by seed.py)
    SEED_ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@irasethpharma.com")
    SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "iraseth2026")
    SEED_ADMIN_NAME = os.getenv("SEED_ADMIN_NAME", "Iraseth Admin")

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
