from flask import Blueprint, request, jsonify, g

from extensions import db
from utils.security import (
    check_password, issue_token, close_session, require_role,
)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = db.users.find_one({"email": email})
    if not user or not check_password(password, user["password_hash"]):
        return jsonify({"error": "Incorrect email or password."}), 401

    token, jti = issue_token(user)
    return jsonify({
        "token": token,
        "user": {
            "email": user["email"],
            "name": user.get("name", ""),
            "role": user["role"],
        },
    })


@bp.post("/logout")
@require_role()
def logout():
    """Stamps the matching session log with logout_at + duration."""
    close_session(g.user["jti"])
    return jsonify({"ok": True})


@bp.get("/me")
@require_role()
def me():
    return jsonify({
        "email": g.user["email"],
        "name": g.user.get("name", ""),
        "role": g.user["role"],
    })
