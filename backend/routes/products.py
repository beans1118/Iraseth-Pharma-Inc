"""
Product catalog. Superadmin is the only role that can create a product.
Quantity changes only through /api/inventory so stock changes stay audited.

Phase 3 adds optional pagination and safer search without changing the
existing response shape. When page/limit are omitted, existing frontend
behavior remains unchanged.
"""
from datetime import datetime, timezone
import re

from flask import Blueprint, request, jsonify, g, make_response
from pymongo.errors import DuplicateKeyError

from config import Config
from extensions import db
from utils.security import require_role
from realtime import emit_inventory_log

bp = Blueprint("products", __name__, url_prefix="/api/products")

REQUIRED_FIELDS = ["id", "name", "description", "category", "unit", "quantity"]
OPTIONAL_FIELDS = ["price"]


def _status(p: dict) -> str:
    qty = p.get("quantity", 0)
    if qty <= 0:
        return "out-of-stock"
    baseline = p.get("baseline_qty", 0)
    if baseline > 0 and qty * 10 <= baseline * 3:
        return "low-stock"
    return "in-stock"


def _serialize(p: dict) -> dict:
    p = dict(p)
    p.pop("_id", None)
    p["status"] = _status(p)
    return p


def _optional_pagination():
    """Return (page, limit) only when the caller explicitly requests it."""
    if "page" not in request.args and "limit" not in request.args:
        return None, None

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = max(1, int(request.args.get("limit", 50)))
    except (TypeError, ValueError):
        return "error", "error"

    return page, min(limit, Config.API_MAX_PAGE_SIZE)


def _json_list(items, total=None, page=None, limit=None):
    response = make_response(jsonify(items))
    if total is not None:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(limit)
    return response


@bp.get("")
@require_role()
def list_products():
    """Supports ?category=&q=&page=&limit=."""
    query = {}
    category = request.args.get("category")
    if category and category != "all":
        query["category"] = category

    q = (request.args.get("q") or "").strip()
    if q:
        safe_q = re.escape(q)
        query["$or"] = [
            {"name": {"$regex": safe_q, "$options": "i"}},
            # Product IDs normally behave like prefixes; anchoring allows
            # MongoDB to use the ID index more effectively.
            {"id": {"$regex": f"^{safe_q}", "$options": "i"}},
        ]

    page, limit = _optional_pagination()
    if page == "error":
        return jsonify({"error": "page and limit must be whole numbers."}), 400

    cursor = db.products.find(query).sort("id", 1)

    if page is None:
        return jsonify([_serialize(p) for p in cursor])

    total = db.products.count_documents(query)
    cursor = cursor.skip((page - 1) * limit).limit(limit)
    return _json_list(
        [_serialize(p) for p in cursor],
        total=total,
        page=page,
        limit=limit,
    )


@bp.get("/<product_id>")
@require_role()
def get_product(product_id):
    p = db.products.find_one({"id": product_id})
    if not p:
        return jsonify({"error": "Product not found."}), 404
    return jsonify(_serialize(p))


@bp.post("")
@require_role("superadmin")
def create_product():
    data = request.get_json(silent=True) or {}
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    doc = {f: data[f] for f in REQUIRED_FIELDS}
    for f in OPTIONAL_FIELDS:
        doc[f] = data.get(f, 0)

    try:
        doc["quantity"] = int(doc["quantity"])
        doc["price"] = float(doc["price"])
    except (TypeError, ValueError):
        return jsonify({"error": "quantity and price must be numbers."}), 400

    if doc["quantity"] < 0:
        return jsonify({"error": "quantity cannot be negative."}), 400

    doc["baseline_qty"] = doc["quantity"]

    try:
        db.products.insert_one(doc)
    except DuplicateKeyError:
        return jsonify({"error": f"Product {doc['id']} already exists."}), 409

    if doc["quantity"] > 0:
        opening_log = {
            "product_id": doc["id"],
            "product_name": doc["name"],
            "action": "opening",
            "qty": doc["quantity"],
            "before": 0,
            "after": doc["quantity"],
            "note": "Opening stock",
            "actor_email": g.user["email"],
            "actor_name": g.user.get("name", ""),
            "role": g.user["role"],
            "at": datetime.now(timezone.utc).isoformat(),
        }
        db.inventory_logs.insert_one(opening_log)
        opening_log.pop("_id", None)
        emit_inventory_log(opening_log)

    return jsonify(_serialize(doc)), 201


@bp.put("/<product_id>")
@require_role("superadmin")
def update_product(product_id):
    """Edits product metadata. Quantity only changes through /api/inventory."""
    data = request.get_json(silent=True) or {}
    editable = [f for f in REQUIRED_FIELDS + OPTIONAL_FIELDS if f != "quantity"]
    updates = {f: data[f] for f in editable if f in data}

    if "price" in updates:
        try:
            updates["price"] = float(updates["price"])
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a number."}), 400

    if not updates:
        return jsonify({"error": "No valid fields to update."}), 400

    try:
        result = db.products.update_one({"id": product_id}, {"$set": updates})
    except DuplicateKeyError:
        return jsonify({"error": f"Product {updates.get('id')} already exists."}), 409

    if result.matched_count == 0:
        return jsonify({"error": "Product not found."}), 404

    lookup_id = updates.get("id", product_id)
    return jsonify(_serialize(db.products.find_one({"id": lookup_id})))


@bp.delete("/<product_id>")
@require_role("superadmin")
def delete_product(product_id):
    result = db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"deleted": product_id})
