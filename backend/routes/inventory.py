"""
This is the Inventory Tracking System itself: current stock levels, "release"
(a product went out — deducts quantity) and "supply" (restock — adds
quantity). Every change writes one row to inventory_logs (who, role, product,
before/after quantity, note, timestamp) and pushes a live update over
Socket.IO so every open dashboard reflects it immediately — no refresh.

Role rules:
  - superadmin & subadmin can release/supply.
  - admin is view-only (enforced below — it can list products, but the
    write endpoints reject it with a 403).
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from extensions import db
from utils.security import require_role
from realtime import emit_stock_update, emit_inventory_log
from routes.products import _serialize

bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


def _log_and_apply(product_id: str, delta: int, action: str, note: str):
    product = db.products.find_one({"id": product_id})
    if not product:
        return None, ("Product not found.", 404)

    before = product.get("quantity", 0)
    after = before + delta
    if after < 0:
        return None, (f"Cannot release {abs(delta)} — only {before} in stock.", 400)

    db.products.update_one({"id": product_id}, {"$set": {"quantity": after}})
    updated = db.products.find_one({"id": product_id})

    log_entry = {
        "product_id": product_id,
        "product_name": updated.get("name", ""),
        "action": action,          # "release" | "supply"
        "qty": abs(delta),
        "before": before,
        "after": after,
        "note": note,
        "actor_email": g.user["email"],
        "actor_name": g.user.get("name", ""),
        "role": g.user["role"],
        "at": datetime.now(timezone.utc).isoformat(),
    }
    db.inventory_logs.insert_one(log_entry)
    log_entry.pop("_id", None)

    serialized = _serialize(updated)
    emit_stock_update(serialized)
    emit_inventory_log(log_entry)
    return (serialized, log_entry), None


@bp.get("")
@require_role()
def list_stock():
    """Live stock board. Any authenticated staff role can view."""
    products = [_serialize(p) for p in db.products.find().sort("id", 1)]
    return jsonify(products)


@bp.post("/<product_id>/release")
@require_role("superadmin", "subadmin")
def release_stock(product_id):
    """A product went out (fulfilled to a customer, damaged, etc). Deducts stock."""
    data = request.get_json(silent=True) or {}
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "qty must be a whole number."}), 400
    if qty <= 0:
        return jsonify({"error": "qty must be greater than zero."}), 400

    result, err = _log_and_apply(product_id, -qty, "release", (data.get("note") or "").strip())
    if err:
        return jsonify({"error": err[0]}), err[1]
    product, log_entry = result
    return jsonify({"product": product, "log": log_entry}), 200


@bp.post("/<product_id>/supply")
@require_role("superadmin", "subadmin")
def add_supply(product_id):
    """Restock — use when a product is low/out of stock and new supply arrives."""
    data = request.get_json(silent=True) or {}
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "qty must be a whole number."}), 400
    if qty <= 0:
        return jsonify({"error": "qty must be greater than zero."}), 400

    result, err = _log_and_apply(product_id, qty, "supply", (data.get("note") or "").strip())
    if err:
        return jsonify({"error": err[0]}), err[1]
    product, log_entry = result
    return jsonify({"product": product, "log": log_entry}), 200
