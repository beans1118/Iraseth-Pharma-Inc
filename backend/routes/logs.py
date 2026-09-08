"""
Audit trail. Superadmin sees every log; Admin is view-only for these same
logs (that's their entire job per the role rules); Sub-admin has no access
to this blueprint at all.
"""
from flask import Blueprint, request, jsonify

from extensions import db
from utils.security import require_role

bp = Blueprint("logs", __name__, url_prefix="/api/logs")


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


@bp.get("/sessions")
@require_role("superadmin", "admin")
def session_logs():
    """Who logged in/out, when, how long, and as which role.
    Supports ?role=&user=&limit=."""
    query = {}
    role = request.args.get("role")
    if role and role != "all":
        query["role"] = role
    user = request.args.get("user")
    if user:
        query["user_email"] = {"$regex": user, "$options": "i"}

    limit = min(int(request.args.get("limit", 200)), 1000)
    rows = [_serialize(s) for s in db.sessions.find(query).sort("login_at", -1).limit(limit)]
    return jsonify(rows)


@bp.get("/inventory")
@require_role("superadmin", "admin")
def inventory_logs():
    """Every stock add/release: who, role, product, qty, before/after, when.
    Supports ?action=release|supply&product=&limit=."""
    query = {}
    action = request.args.get("action")
    if action and action != "all":
        query["action"] = action
    product = request.args.get("product")
    if product:
        query["product_id"] = product

    limit = min(int(request.args.get("limit", 200)), 1000)
    rows = [_serialize(l) for l in db.inventory_logs.find(query).sort("at", -1).limit(limit)]
    return jsonify(rows)
