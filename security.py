"""
Password hashing (bcrypt) and JWT issuing/verification, plus a decorator
that protects admin-only routes.
"""
from functools import wraps
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from flask import request, jsonify, g

from config import Config


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def issue_token(admin: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin["_id"]),
        "email": admin["email"],
        "name": admin.get("name", ""),
        "iat": now,
        "exp": now + timedelta(hours=Config.JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])


def require_admin(fn):
    """Protects a route: requires 'Authorization: Bearer <token>' with a valid, unexpired JWT."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header."}), 401
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired. Please sign in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid authentication token."}), 401
        g.admin = payload
        return fn(*args, **kwargs)
    return wrapper
