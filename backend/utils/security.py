"""
Security helpers for password hashing, JWT/session validation, role-aware route
protection, and distributed fixed-window API rate limiting.
"""
import hashlib
import uuid
from functools import wraps
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from flask import request, jsonify, g
from pymongo import ReturnDocument

from config import Config
from extensions import db
from realtime import emit_session_log


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(
        plain_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def check_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def issue_token(user: dict):
    """Return (token, jti) and open the audited login session."""
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
        # ProxyFix, when enabled in app.py, makes remote_addr represent the
        # trusted client address instead of trusting a raw user-supplied header.
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
    }
    db.sessions.insert_one(session_doc)
    session_doc.pop("_id", None)
    emit_session_log(session_doc)

    return token, jti


def close_session(jti: str):
    """Atomically revoke a JWT session and stamp logout metadata."""
    now = datetime.now(timezone.utc)

    existing = db.sessions.find_one({"jti": jti, "logout_at": None})
    if not existing:
        return None

    login_at = datetime.fromisoformat(existing["login_at"])
    duration = int((now - login_at).total_seconds())

    session_doc = db.sessions.find_one_and_update(
        {"jti": jti, "logout_at": None},
        {
            "$set": {
                "logout_at": now.isoformat(),
                "duration_seconds": duration,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not session_doc:
        return None

    session_doc.pop("_id", None)
    emit_session_log(session_doc)
    return session_doc


def decode_token(token: str) -> dict:
    return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])


def authenticate_token(token: str, allowed_roles=None):
    """
    Validate JWT signature/expiry and confirm the matching session is still
    active. Returns (payload, None) or (None, (message, status_code)).
    """
    if not token:
        return None, ("Missing authentication token.", 401)

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        return None, ("Session expired. Please sign in again.", 401)
    except jwt.InvalidTokenError:
        return None, ("Invalid authentication token.", 401)

    jti = payload.get("jti")
    if not jti:
        return None, ("Invalid authentication token.", 401)

    session = db.sessions.find_one(
        {"jti": jti, "logout_at": None},
        {"role": 1, "user_email": 1},
    )
    if not session:
        return None, ("Session is no longer active. Please sign in again.", 401)

    # The role in the active session must still match the signed token.
    if session.get("role") != payload.get("role"):
        return None, ("Session role is no longer valid. Please sign in again.", 401)

    if allowed_roles and payload.get("role") not in allowed_roles:
        return None, ("You do not have permission to do that.", 403)

    return payload, None


def require_role(*roles):
    """Protect a route and enforce active-session + role validation."""
    allowed = roles or tuple(Config.ROLES)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or malformed Authorization header."}), 401

            token = auth_header.split(" ", 1)[1].strip()
            payload, error = authenticate_token(token, allowed_roles=allowed)
            if error:
                return jsonify({"error": error[0]}), error[1]

            g.admin = payload  # backward compatibility
            g.user = payload
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _rate_limit_bucket(scope: str, principal: str, window_seconds: int):
    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp()) // window_seconds
    principal_hash = hashlib.sha256(principal.encode("utf-8")).hexdigest()[:24]
    return now, bucket, f"{scope}:{principal_hash}:{bucket}"


def check_rate_limit(scope: str, limit: int, window_seconds: int, principal: str):
    """
    Distributed fixed-window limiter backed by MongoDB.
    Returns (allowed, retry_after_seconds).
    """
    now, bucket, key = _rate_limit_bucket(scope, principal, window_seconds)
    expires_at = now + timedelta(seconds=window_seconds * 2)

    row = db.rate_limits.find_one_and_update(
        {"_id": key},
        {
            "$inc": {"count": 1},
            "$setOnInsert": {
                "scope": scope,
                "expires_at": expires_at,
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    if row.get("count", 0) <= limit:
        return True, 0

    next_window = (bucket + 1) * window_seconds
    retry_after = max(1, next_window - int(now.timestamp()))
    return False, retry_after


def client_rate_limit(scope: str, limit: int, window_seconds: int = 60):
    """Rate limit the current client address and return a Flask response if hit."""
    principal = request.remote_addr or "unknown"
    allowed, retry_after = check_rate_limit(
        scope=scope,
        limit=limit,
        window_seconds=window_seconds,
        principal=principal,
    )
    if allowed:
        return None

    response = jsonify({
        "error": "Too many requests. Please try again shortly.",
        "retry_after": retry_after,
    })
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


# Backward-compatible alias.
require_admin = require_role()
