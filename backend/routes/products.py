"""
Product catalog. Superadmin is the only role that can create a product at
all (per the role rules — see PROPOSAL.md) — everyone else only changes an
existing product's quantity, and only through /api/inventory (release/supply),
never here.
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from extensions import db
from utils.security import require_role
from realtime import emit_inventory_log

bp = Blueprint("products", __name__, url_prefix="/api/products")

REQUIRED_FIELDS = ["id", "name", "description", "category", "unit", "quantity", "reorder_level"]
OPTIONAL_FIELDS = ["price"]


def _status(p: dict) -> str:
    qty = p.get("quantity", 0)
    reorder = p.get("reorder_level", 0)
    if qty <= 0:
        return "out-of-stock"
    if qty <= reorder:
        return "low-stock"
    return "in-stock"


def _serialize(p: dict) -> dict:
    p = dict(p)
    p.pop("_id", None)
    p["status"] = _status(p)
    return p


@bp.get("")
@require_role()
def list_products():
    """Any authenticated staff role. Supports ?category=&q=."""
    query = {}
    category = request.args.get("category")
    if category and category != "all":
        query["category"] = category

    q = (request.args.get("q") or "").strip()
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"id": {"$regex": q, "$options": "i"}},
        ]

    products = [_serialize(p) for p in db.products.find(query).sort("id", 1)]
    return jsonify(products)


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

    if db.products.find_one({"id": data["id"]}):
        return jsonify({"error": f"Product {data['id']} already exists."}), 409

    doc = {f: data[f] for f in REQUIRED_FIELDS}
    for f in OPTIONAL_FIELDS:
        doc[f] = data.get(f, 0)

    try:
        doc["quantity"] = int(doc["quantity"])
        doc["reorder_level"] = int(doc["reorder_level"])
        doc["price"] = float(doc["price"])
    except (TypeError, ValueError):
        return jsonify({"error": "quantity, reorder_level, and price must be numbers."}), 400

    db.products.insert_one(doc)

    # Log the beginning stock the moment this product enters the system —
    # otherwise a product's quantity history has no starting point, just
    # release/supply deltas with nothing to measure them against.
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
    """Edits name/description/category/unit/reorder_level/price. NOT quantity —
    quantity only ever changes through /api/inventory, so every stock change
    is logged."""
    data = request.get_json(silent=True) or {}
    editable = [f for f in REQUIRED_FIELDS + OPTIONAL_FIELDS if f != "quantity"]
    updates = {f: data[f] for f in editable if f in data}
    if "reorder_level" in updates:
        try:
            updates["reorder_level"] = int(updates["reorder_level"])
        except (TypeError, ValueError):
            return jsonify({"error": "reorder_level must be a number."}), 400
    if "price" in updates:
        try:
            updates["price"] = float(updates["price"])
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a number."}), 400
    if not updates:
        return jsonify({"error": "No valid fields to update."}), 400

    result = db.products.update_one({"id": product_id}, {"$set": updates})
    if result.matched_count == 0:
        return jsonify({"error": "Product not found."}), 404

    return jsonify(_serialize(db.products.find_one({"id": product_id})))


@bp.delete("/<product_id>")
@require_role("superadmin")
def delete_product(product_id):
    result = db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"deleted": product_id})
