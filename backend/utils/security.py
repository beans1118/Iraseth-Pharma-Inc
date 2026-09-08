"""
Password hashing (bcrypt), JWT issuing/verification, and the role-aware
`require_role` decorator that protects backend routes.

Every login creates one row in `sessions` (login_at, jti, role, ...).
Every logout finds that row by jti and stamps logout_at + duration, which is
how the "who logged in/out, when, for how long, as what role" log is built —
there is no separate manual logging step routes need to remember to call.
"""
import uuid
from functools import wraps
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from flask import request, jsonify, g

from config import Config
from extensions import db
from realtime import emit_session_log


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def issue_token(user: dict):
    """Returns (token, jti). Also writes the opening half of the session log."""
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user["_id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user["role"],
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(hours=Config.JWT_EXPIRES_HOURS),
    }
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")

    session_doc = {
        "jti": jti,
        "user_email": user["email"],
        "user_name": user.get("name", ""),
        "role": user["role"],
        "login_at": now.isoformat(),
        "logout_at": None,
        "duration_seconds": None,
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent", ""),
    }
    db.sessions.insert_one(session_doc)
    session_doc.pop("_id", None)
    emit_session_log(session_doc)

    return token, jti


def close_session(jti: str):
    """Stamps logout_at + duration_seconds on the matching session log row."""
    session_doc = db.sessions.find_one({"jti": jti})
    if not session_doc or session_doc.get("logout_at"):
        return None

    now = datetime.now(timezone.utc)
    login_at = datetime.fromisoformat(session_doc["login_at"])
    duration = int((now - login_at).total_seconds())

    db.sessions.update_one(
        {"jti": jti},
        {"$set": {"logout_at": now.isoformat(), "duration_seconds": duration}},
    )
    session_doc["logout_at"] = now.isoformat()
    session_doc["duration_seconds"] = duration
    session_doc.pop("_id", None)
    emit_session_log(session_doc)
    return session_doc


def decode_token(token: str) -> dict:
    return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])


def require_role(*roles):
    """
    Protects a route: requires 'Authorization: Bearer <token>' with a valid,
    unexpired JWT whose role is one of `roles`. Pass no roles to just require
    "any authenticated staff member" (superadmin, admin, or subadmin).
    """
    allowed = roles or tuple(Config.ROLES)

    def decorator(fn):
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

            if payload.get("role") not in allowed:
                return jsonify({"error": "You do not have permission to do that."}), 403

            g.admin = payload  # kept as g.admin for backward compatibility with existing routes
            g.user = payload
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# Backward-compatible alias: any authenticated staff member, regardless of role.
require_admin = require_role()
