from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from extensions import db
from utils.security import require_role
from realtime import emit_stock_update, emit_inventory_log
from routes.products import _serialize

bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


def _ensure_monthly_openings():
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    if db.inventory_logs.count_documents({"action": "monthly_opening", "month": month_key}) > 0:
        return  # already snapshotted this month

    now = datetime.now(timezone.utc).isoformat()
    logs = []
    for p in db.products.find():
        qty = p.get("quantity", 0)
        logs.append({
            "product_id": p["id"],
            "product_name": p.get("name", ""),
            "action": "monthly_opening",
            "qty": qty,
            "before": qty,
            "after": qty,
            "note": f"Beginning stock for {month_key}",
            "month": month_key,
            "actor_email": "system@irasethpharma.com",
            "actor_name": "System (monthly snapshot)",
            "role": "superadmin",
            "at": now,
        })
    if logs:
        db.inventory_logs.insert_many(logs)


def _log_and_apply(product_id: str, delta: int, action: str, note: str):
    product = db.products.find_one({"id": product_id})
    if not product:
        return None, ("Product not found.", 404)

    before = product.get("quantity", 0)
    after = before + delta
    if after < 0:
        return None, (f"Cannot release {abs(delta)} — only {before} in stock.", 400)

    updates = {"quantity": after}
    # Adding stock resets the "full" baseline used for the 30% low-stock
    # check. Releasing never touches it — releases measure against
    # whatever the last restock brought the shelf up to.
    if action == "supply":
        updates["baseline_qty"] = after
    db.products.update_one({"id": product_id}, {"$set": updates})
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
    _ensure_monthly_openings()
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
