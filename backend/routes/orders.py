from datetime import datetime, timezone
import re

from flask import Blueprint, request, jsonify, g, make_response
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from config import Config
from extensions import db
from utils.security import require_role
from utils.email import order_confirmation_email, order_status_email
from realtime import emit_stock_update, emit_inventory_log
from routes.products import _serialize as serialize_product

bp = Blueprint("orders", __name__, url_prefix="/api/orders")

VALID_STATUSES = ["Pending", "Processing", "Fulfilled"]


class FulfillmentError(Exception):
    """Raised when an order cannot be fulfilled safely."""


def _serialize(o: dict) -> dict:
    o = dict(o)
    o.pop("_id", None)
    return o


def _latest_sequence_for_year(year: int) -> int:
    prefix = f"PO-{year}"
    latest = db.orders.find_one(
        {"id": {"$regex": f"^{prefix}"}},
        sort=[("id", -1)],
        projection={"id": 1},
    )
    if not latest:
        return 0
    try:
        return int(latest["id"].replace(prefix, ""))
    except (TypeError, ValueError):
        return 0


def _next_order_id() -> str:
    """Generate PO-YYYYNNNN using an atomic MongoDB counter."""
    year = datetime.now(timezone.utc).year
    counter_id = f"orders-{year}"

    if db.counters.find_one({"_id": counter_id}) is None:
        initial = _latest_sequence_for_year(year)
        try:
            db.counters.insert_one({"_id": counter_id, "seq": initial})
        except DuplicateKeyError:
            pass

    counter = db.counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER,
    )
    return f"PO-{year}{counter['seq']:04d}"


def _fulfill_order_transaction(order_id: str, note_text: str):
    """
    Atomically mark an order fulfilled, deduct every line item and write the
    inventory logs. Any shortage aborts the entire transaction.

    Requires MongoDB Atlas or another replica-set/sharded deployment that
    supports transactions.
    """
    stock_events = []
    log_events = []

    with db.client.start_session() as session:
        with session.start_transaction():
            order = db.orders.find_one({"id": order_id}, session=session)
            if not order:
                raise FulfillmentError("Order not found.")

            if order.get("status") == "Fulfilled":
                return _serialize(order), [], [], False

            for line in order["lines"]:
                qty = int(line["qty"])
                updated_product = db.products.find_one_and_update(
                    {"id": line["id"], "quantity": {"$gte": qty}},
                    {"$inc": {"quantity": -qty}},
                    return_document=ReturnDocument.AFTER,
                    session=session,
                )

                if not updated_product:
                    existing = db.products.find_one(
                        {"id": line["id"]},
                        {"quantity": 1, "name": 1},
                        session=session,
                    )
                    if not existing:
                        raise FulfillmentError(
                            f"Cannot fulfill order: product {line['id']} no longer exists."
                        )
                    raise FulfillmentError(
                        f"Cannot fulfill order: {line['id']} has only "
                        f"{existing.get('quantity', 0)} in stock; {qty} required."
                    )

                after = updated_product.get("quantity", 0)
                before = after + qty
                log_entry = {
                    "product_id": line["id"],
                    "product_name": updated_product.get("name", ""),
                    "action": "release",
                    "qty": qty,
                    "before": before,
                    "after": after,
                    "note": f"Order {order_id} fulfilled",
                    "actor_email": g.user["email"],
                    "actor_name": g.user.get("name", ""),
                    "role": g.user["role"],
                    "at": datetime.now(timezone.utc).isoformat(),
                }
                db.inventory_logs.insert_one(log_entry, session=session)

                clean_log = dict(log_entry)
                clean_log.pop("_id", None)
                log_events.append(clean_log)
                stock_events.append(serialize_product(updated_product))

            order_update = {"$set": {"status": "Fulfilled"}}
            if note_text:
                order_update["$push"] = {
                    "notes": {
                        "text": note_text,
                        "author": g.user.get("email", "staff"),
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                }

            result = db.orders.update_one(
                {"id": order_id, "status": {"$ne": "Fulfilled"}},
                order_update,
                session=session,
            )
            if result.matched_count != 1:
                raise FulfillmentError(
                    "Order was already fulfilled by another request."
                )

            updated_order = db.orders.find_one({"id": order_id}, session=session)

    # Emit only after commit so clients never see rolled-back stock changes.
    for product in stock_events:
        emit_stock_update(product)
    for log_entry in log_events:
        emit_inventory_log(log_entry)

    return _serialize(updated_order), stock_events, log_events, True


@bp.post("")
def create_order():
    """Public checkout. Prices are always recalculated from the catalog."""
    data = request.get_json(silent=True) or {}
    client = (data.get("client") or "").strip()
    email = (data.get("email") or "").strip()
    facility = (data.get("facility") or "").strip()
    raw_lines = data.get("lines") or []

    if not client or not email or not facility:
        return jsonify({"error": "client, email, and facility are required."}), 400
    if not raw_lines:
        return jsonify({"error": "Order must include at least one line item."}), 400

    if len(raw_lines) > Config.MAX_ORDER_LINES:
        return jsonify({
            "error": f"Order cannot contain more than {Config.MAX_ORDER_LINES} line items."
        }), 400

    # Validate quantities first and collect unique product IDs.
    validated = []
    product_ids = set()
    for raw in raw_lines:
        product_id = raw.get("id")
        if not product_id:
            return jsonify({"error": "Every line item requires a product id."}), 400
        try:
            qty = max(1, int(raw.get("qty", 1)))
        except (TypeError, ValueError):
            return jsonify({"error": f"Invalid quantity for {product_id}"}), 400
        validated.append((product_id, qty))
        product_ids.add(product_id)

    # Phase 3: one MongoDB query for the whole cart instead of one query per
    # order line. This removes the N+1 checkout query pattern.
    products = {
        p["id"]: p
        for p in db.products.find({"id": {"$in": list(product_ids)}})
    }

    missing_ids = [pid for pid in product_ids if pid not in products]
    if missing_ids:
        return jsonify({"error": f"Unknown product id: {missing_ids[0]}"}), 400

    lines = []
    total = 0.0
    for product_id, qty in validated:
        product = products[product_id]
        line_total = round(product.get("price", 0) * qty, 2)
        total += line_total
        lines.append({
            "id": product["id"],
            "name": product["name"],
            "unit": product["unit"],
            "price": product.get("price", 0),
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

    try:
        db.orders.insert_one(order)
    except DuplicateKeyError:
        order["id"] = _next_order_id()
        db.orders.insert_one(order)

    order_confirmation_email(order)
    return jsonify(_serialize(order)), 201


@bp.get("")
@require_role()
def list_orders():
    """Supports ?status=&q=&page=&limit=. Response body remains an array."""
    query = {}
    status = request.args.get("status")
    if status and status != "all":
        query["status"] = status

    q = (request.args.get("q") or "").strip()
    if q:
        safe_q = re.escape(q)
        query["$or"] = [
            {"id": {"$regex": f"^{safe_q}", "$options": "i"}},
            {"client": {"$regex": safe_q, "$options": "i"}},
            {"facility": {"$regex": safe_q, "$options": "i"}},
        ]

    pagination_requested = "page" in request.args or "limit" in request.args
    cursor = db.orders.find(query).sort("date", -1)

    if not pagination_requested:
        return jsonify([_serialize(o) for o in cursor])

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = min(
            max(1, int(request.args.get("limit", 50))),
            Config.API_MAX_PAGE_SIZE,
        )
    except (TypeError, ValueError):
        return jsonify({"error": "page and limit must be whole numbers."}), 400

    total = db.orders.count_documents(query)
    cursor = cursor.skip((page - 1) * limit).limit(limit)
    response = make_response(jsonify([_serialize(o) for o in cursor]))
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(limit)
    return response


@bp.get("/clients-summary")
@require_role()
def clients_summary():
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
@require_role()
def get_order(order_id):
    o = db.orders.find_one({"id": order_id})
    if not o:
        return jsonify({"error": "Order not found."}), 404
    return jsonify(_serialize(o))


@bp.patch("/<order_id>")
@require_role("superadmin", "subadmin")
def update_order(order_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    note_text = (data.get("note") or "").strip()

    order = db.orders.find_one({"id": order_id})
    if not order:
        return jsonify({"error": "Order not found."}), 404

    if status is not None and status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {VALID_STATUSES}"}), 400

    status_changed = status is not None and status != order["status"]
    becoming_fulfilled = (
        status_changed
        and status == "Fulfilled"
        and order["status"] != "Fulfilled"
    )

    if not status_changed and not note_text:
        return jsonify({"error": "Nothing to update — provide status and/or note."}), 400

    if becoming_fulfilled:
        try:
            updated, _, _, changed = _fulfill_order_transaction(order_id, note_text)
        except FulfillmentError as exc:
            message = str(exc)
            status_code = 404 if message == "Order not found." else 409
            return jsonify({"error": message}), status_code

        if changed:
            order_status_email(updated, note=note_text)
        return jsonify(updated)

    op = {}
    if status_changed:
        op["$set"] = {"status": status}
    if note_text:
        op["$push"] = {
            "notes": {
                "text": note_text,
                "author": g.user.get("email", "staff"),
                "at": datetime.now(timezone.utc).isoformat(),
            }
        }

    db.orders.update_one({"id": order_id}, op)
    updated = db.orders.find_one({"id": order_id})

    if status_changed:
        order_status_email(updated, note=note_text)

    return jsonify(_serialize(updated))
