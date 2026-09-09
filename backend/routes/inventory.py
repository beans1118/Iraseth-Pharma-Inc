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


def _ensure_monthly_openings():
    """
    Snapshots every product's current quantity as that calendar month's
    "beginning stock" the first time inventory is checked in a new month.
    There's no scheduler in this app, so this runs lazily instead: cheap to
    check (one count query), and guarantees every month gets exactly one
    opening snapshot per product as soon as anyone loads the Inventory tab
    or Stock Movements after the month rolls over.
    """
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


@bp.get("/activity")
@require_role()
def stock_activity():
    """
    Every release/supply, open to ALL roles (unlike /api/logs/inventory,
    which is superadmin/admin only for the full accountability audit).
    This is the operational "what happened to stock, and when" feed —
    e.g. Sub-admin monitoring releases, or anyone pulling up one product's
    full quantity history (500 on Sept 1 -> 10 on Sept 10 -> resupplied
    Sept 12) via ?product=<id>.
    """
    _ensure_monthly_openings()
    query = {}
    action = request.args.get("action")
    if action and action != "all":
        query["action"] = action
    product = request.args.get("product")
    if product:
        query["product_id"] = product

    limit = min(int(request.args.get("limit", 200)), 1000)
    # When looking at one product's full trail, read it chronologically
    # (beginning stock first, most recent last). Otherwise show the
    # general activity feed newest-first.
    sort_dir = 1 if product else -1
    rows = []
    for l in db.inventory_logs.find(query).sort("at", sort_dir).limit(limit):
        l = dict(l)
        l.pop("_id", None)
        rows.append(l)
    return jsonify(rows)
