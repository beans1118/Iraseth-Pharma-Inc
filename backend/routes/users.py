"""
Superadmin-only: create staff accounts, change roles, remove accounts.
This is the only place roles get assigned — nobody can promote themselves.
"""
from flask import Blueprint, request, jsonify, make_response

from config import Config
from extensions import db
from utils.security import require_role, hash_password

bp = Blueprint("users", __name__, url_prefix="/api/users")


def _serialize(u: dict) -> dict:
    u = dict(u)
    u.pop("_id", None)
    u.pop("password_hash", None)
    return u


@bp.get("")
@require_role("superadmin")
def list_users():
    if "page" not in request.args and "limit" not in request.args:
        return jsonify([_serialize(u) for u in db.users.find().sort("email", 1)])

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except (TypeError, ValueError):
        return jsonify({"error": "page and limit must be whole numbers."}), 400

    total = db.users.count_documents({})
    cursor = db.users.find().sort("email", 1).skip((page - 1) * limit).limit(limit)
    response = make_response(jsonify([_serialize(u) for u in cursor]))
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(limit)
    return response


@bp.post("")
@require_role("superadmin")
def create_user():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip()
    role = data.get("role")

    if not email or not password or not name:
        return jsonify({"error": "email, password, and name are required."}), 400
    if role not in Config.ROLES:
        return jsonify({"error": f"role must be one of {Config.ROLES}"}), 400
    if db.users.find_one({"email": email}):
        return jsonify({"error": f"A user with email {email} already exists."}), 409

    doc = {
        "email": email,
        "name": name,
        "role": role,
        "password_hash": hash_password(password),
    }
    db.users.insert_one(doc)
    return jsonify(_serialize(doc)), 201


@bp.patch("/<email>")
@require_role("superadmin")
def update_user(email):
    """Change role, name, or password. Body may include any of: role, name, password."""
    data = request.get_json(silent=True) or {}
    updates = {}
    if "role" in data:
        if data["role"] not in Config.ROLES:
            return jsonify({"error": f"role must be one of {Config.ROLES}"}), 400
        updates["role"] = data["role"]
    if "name" in data:
        updates["name"] = (data["name"] or "").strip()
    if "password" in data and data["password"]:
        updates["password_hash"] = hash_password(data["password"])

    if not updates:
        return jsonify({"error": "Nothing to update."}), 400

    result = db.users.update_one({"email": email.strip().lower()}, {"$set": updates})
    if result.matched_count == 0:
        return jsonify({"error": "User not found."}), 404
    return jsonify(_serialize(db.users.find_one({"email": email.strip().lower()})))


@bp.delete("/<email>")
@require_role("superadmin")
def delete_user(email):
    result = db.users.delete_one({"email": email.strip().lower()})
    if result.deleted_count == 0:
        return jsonify({"error": "User not found."}), 404
    return jsonify({"deleted": email})
