from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, g

from extensions import db
from utils.security import require_admin
from utils.email import order_confirmation_email, order_status_email

bp = Blueprint("orders", __name__, url_prefix="/api/orders")

VALID_STATUSES = ["Pending", "Processing", "Fulfilled"]


def _serialize(o: dict) -> dict:
    o = dict(o)
    o.pop("_id", None)
    return o


def _next_order_id() -> str:
    """PO-YYYYNNNN, sequential per year, e.g. PO-20260034."""
    year = datetime.now(timezone.utc).year
    prefix = f"PO-{year}"
    latest = db.orders.find_one(
        {"id": {"$regex": f"^{prefix}"}}, sort=[("id", -1)]
    )
    if latest:
        seq = int(latest["id"].replace(prefix, "")) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


@bp.post("")
def create_order():
    """Public. The storefront calls this on checkout — no login required."""
    data = request.get_json(silent=True) or {}
    client = (data.get("client") or "").strip()
    email = (data.get("email") or "").strip()
    facility = (data.get("facility") or "").strip()
    raw_lines = data.get("lines") or []

    if not client or not email or not facility:
        return jsonify({"error": "client, email, and facility are required."}), 400
    if not raw_lines:
        return jsonify({"error": "Order must include at least one line item."}), 400

    # Re-price every line server-side from the product catalog — never trust
    # prices sent from the browser.
    lines = []
    total = 0.0
    for raw in raw_lines:
        product = db.products.find_one({"id": raw.get("id")})
        if not product:
            return jsonify({"error": f"Unknown product id: {raw.get('id')}"}), 400
        try:
            qty = max(1, int(raw.get("qty", 1)))
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid quantity for {raw.get('id')}"}), 400

        line_total = round(product["price"] * qty, 2)
        total += line_total
        lines.append({
            "id": product["id"],
            "name": product["name"],
            "unit": product["unit"],
            "price": product["price"],
            "qty": qty,
            "lineTotal": line_total,
        })

    order = {
        "id": _next_order_id(),
        "client": client,
        "email": email,
        "facility": facility,
        "lines": lines,
        "total": round(total, 2),
        "status": "Pending",
        "notes": [],
        "date": datetime.now(timezone.utc).isoformat(),
    }
    db.orders.insert_one(order)
    order_confirmation_email(order)

    return jsonify(_serialize(order)), 201


@bp.get("")
@require_admin
def list_orders():
    """Admin only. Supports ?status=&q=."""
    query = {}
    status = request.args.get("status")
    if status and status != "all":
        query["status"] = status

    q = (request.args.get("q") or "").strip()
    if q:
        query["$or"] = [
            {"id": {"$regex": q, "$options": "i"}},
            {"client": {"$regex": q, "$options": "i"}},
            {"facility": {"$regex": q, "$options": "i"}},
        ]

    orders = [_serialize(o) for o in db.orders.find(query).sort("date", -1)]
    return jsonify(orders)


@bp.get("/clients-summary")
@require_admin
def clients_summary():
    """Admin only. Purchase totals grouped by facility, for the Clients view."""
    pipeline = [
        {"$group": {
            "_id": "$facility",
            "client": {"$first": "$client"},
            "orders": {"$sum": 1},
            "spend": {"$sum": "$total"},
            "last": {"$max": "$date"},
        }},
        {"$sort": {"spend": -1}},
    ]
    rows = list(db.orders.aggregate(pipeline))
    for r in rows:
        r["facility"] = r.pop("_id")
    return jsonify(rows)


@bp.get("/<order_id>")
@require_admin
def get_order(order_id):
    o = db.orders.find_one({"id": order_id})
    if not o:
        return jsonify({"error": "Order not found."}), 404
    return jsonify(_serialize(o))


@bp.patch("/<order_id>")
@require_admin
def update_order(order_id):
    """Admin only. Body may include 'status' and/or 'note'. Emails the client on status change."""
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    note_text = (data.get("note") or "").strip()

    order = db.orders.find_one({"id": order_id})
    if not order:
        return jsonify({"error": "Order not found."}), 404

    updates = {}
    status_changed = False
    if status is not None:
        if status not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400
        status_changed = status != order["status"]
        updates["status"] = status

    push = None
    if note_text:
        push = {"notes": {
            "text": note_text,
            "author": g.admin.get("email", "admin"),
            "at": datetime.now(timezone.utc).isoformat(),
        }}

    if not updates and not push:
        return jsonify({"error": "Nothing to update — provide status and/or note."}), 400

    op = {}
    if updates:
        op["$set"] = updates
    if push:
        op["$push"] = push
    db.orders.update_one({"id": order_id}, op)

    updated = db.orders.find_one({"id": order_id})
    if status_changed:
        order_status_email(updated, note=note_text)

    return jsonify(_serialize(updated))
