from flask import Blueprint, request, jsonify, g

from extensions import db
from utils.security import check_password, issue_token, require_admin

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    admin = db.admins.find_one({"email": email})
    if not admin or not check_password(password, admin["password_hash"]):
        return jsonify({"error": "Incorrect email or password."}), 401

    token = issue_token(admin)
    return jsonify({
        "token": token,
        "admin": {"email": admin["email"], "name": admin.get("name", "")},
    })


@bp.get("/me")
@require_admin
def me():
    return jsonify({"email": g.admin["email"], "name": g.admin.get("name", "")})
