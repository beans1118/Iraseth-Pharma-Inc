"""
Inventory tracking: current stock, release, supply and monthly opening snapshots.

Phase 1 hardening:
- stock changes are atomic
- a release can never make quantity negative
- monthly opening snapshots are race-safe and unique per product/month
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g
from pymongo import ReturnDocument, UpdateOne
from pymongo.errors import BulkWriteError

from extensions import db
from utils.security import require_role
from realtime import emit_stock_update, emit_inventory_log
from routes.products import _serialize

bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


def _ensure_monthly_openings():
    """Create one beginning-stock snapshot per product for the current month."""
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")

    product_count = db.products.count_documents({})
    existing_count = db.inventory_logs.count_documents(
        {"action": "monthly_opening", "month": month_key}
    )
    if existing_count >= product_count:
        return

    now = datetime.now(timezone.utc).isoformat()
    operations = []

    for p in db.products.find({}, {"id": 1, "name": 1, "quantity": 1}):
        qty = p.get("quantity", 0)
        doc = {
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
        }
        operations.append(
            UpdateOne(
                {
                    "action": "monthly_opening",
                    "month": month_key,
                    "product_id": p["id"],
                },
                {"$setOnInsert": doc},
                upsert=True,
            )
        )

    if operations:
        try:
            db.inventory_logs.bulk_write(operations, ordered=False)
        except BulkWriteError as exc:
            non_duplicate_errors = [
                e for e in exc.details.get("writeErrors", [])
                if e.get("code") != 11000
            ]
            if non_duplicate_errors:
                raise


def _log_and_apply(product_id: str, delta: int, action: str, note: str):
    """Atomically change stock and then write the audit entry."""
    if action == "release":
        requested = abs(delta)
        updated = db.products.find_one_and_update(
            {"id": product_id, "quantity": {"$gte": requested}},
            {"$inc": {"quantity": -requested}},
            return_document=ReturnDocument.AFTER,
        )

        if not updated:
            existing = db.products.find_one({"id": product_id}, {"quantity": 1})
            if not existing:
                return None, ("Product not found.", 404)
            available = existing.get("quantity", 0)
            return None, (
                f"Cannot release {requested} — only {available} in stock.",
                400,
            )

        after = updated.get("quantity", 0)
        before = after + requested
        amount = requested

    elif action == "supply":
        amount = abs(delta)
        updated = db.products.find_one_and_update(
            {"id": product_id},
            [
                {
                    "$set": {
                        "quantity": {
                            "$add": [
                                {"$ifNull": ["$quantity", 0]},
                                amount,
                            ]
                        }
                    }
                },
                {"$set": {"baseline_qty": "$quantity"}},
            ],
            return_document=ReturnDocument.AFTER,
        )

        if not updated:
            return None, ("Product not found.", 404)

        after = updated.get("quantity", 0)
        before = after - amount

    else:
        return None, ("Invalid inventory action.", 400)

    log_entry = {
        "product_id": product_id,
        "product_name": updated.get("name", ""),
        "action": action,
        "qty": amount,
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
    data = request.get_json(silent=True) or {}
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "qty must be a whole number."}), 400

    if qty <= 0:
        return jsonify({"error": "qty must be greater than zero."}), 400

    result, err = _log_and_apply(
        product_id,
        -qty,
        "release",
        (data.get("note") or "").strip(),
    )
    if err:
        return jsonify({"error": err[0]}), err[1]

    product, log_entry = result
    return jsonify({"product": product, "log": log_entry}), 200


@bp.post("/<product_id>/supply")
@require_role("superadmin", "subadmin")
def add_supply(product_id):
    data = request.get_json(silent=True) or {}
    try:
        qty = int(data.get("qty", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "qty must be a whole number."}), 400

    if qty <= 0:
        return jsonify({"error": "qty must be greater than zero."}), 400

    result, err = _log_and_apply(
        product_id,
        qty,
        "supply",
        (data.get("note") or "").strip(),
    )
    if err:
        return jsonify({"error": err[0]}), err[1]

    product, log_entry = result
    return jsonify({"product": product, "log": log_entry}), 200
