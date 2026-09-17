"""
Audit trail. Superadmin and Admin can view logs; Sub-admin has no access.

Phase 3 keeps the existing array response but adds safe pagination through
?page=&limit= so the UI can load logs in smaller chunks when needed.
"""
import re

from flask import Blueprint, request, jsonify, make_response

from config import Config
from extensions import db
from utils.security import require_role

bp = Blueprint("logs", __name__, url_prefix="/api/logs")


def _serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    return doc


def _page_limit(default_limit=200):
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(
            max(1, int(request.args.get("limit", default_limit))),
            min(1000, Config.API_MAX_PAGE_SIZE),
        )
        return page, limit, None
    except (TypeError, ValueError):
        return None, None, (
            jsonify({"error": "page and limit must be whole numbers."}),
            400,
        )


def _paged_response(collection, query, sort_field, page, limit):
    total = collection.count_documents(query)
    rows = [
        _serialize(row)
        for row in collection.find(query)
        .sort(sort_field, -1)
        .skip((page - 1) * limit)
        .limit(limit)
    ]
    response = make_response(jsonify(rows))
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(limit)
    return response


@bp.get("/sessions")
@require_role("superadmin", "admin")
def session_logs():
    """Supports ?role=&user=&page=&limit=."""
    query = {}
    role = request.args.get("role")
    if role and role != "all":
        query["role"] = role

    user = (request.args.get("user") or "").strip()
    if user:
        query["user_email"] = {"$regex": re.escape(user), "$options": "i"}

    page, limit, error = _page_limit()
    if error:
        return error

    return _paged_response(db.sessions, query, "login_at", page, limit)


@bp.get("/inventory")
@require_role("superadmin", "admin")
def inventory_logs():
    """Supports ?action=release|supply&product=&page=&limit=."""
    query = {}
    action = request.args.get("action")
    if action and action != "all":
        query["action"] = action

    product = request.args.get("product")
    if product:
        query["product_id"] = product

    page, limit, error = _page_limit()
    if error:
        return error

    return _paged_response(db.inventory_logs, query, "at", page, limit)
