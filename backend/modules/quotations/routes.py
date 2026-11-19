"""Public inquiry workflow. Acceptance creates a pending order; stock changes only in the Orders workflow."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from uuid import uuid4
import json
import re
from flask import Blueprint, jsonify, request, g
from pymongo.errors import DuplicateKeyError
from extensions import db
from utils.security import require_role
from modules.public_catalog.routes import _availability_map, _as_public_price
from modules.product_metadata import identity_pending, IDENTITY_REQUIRED

public_bp = Blueprint("public_quotations", __name__, url_prefix="/api/public/quotations")
staff_bp = Blueprint("staff_quotations", __name__, url_prefix="/api/v2/quotations")
ALLOWED_STATUS = ("New", "In Review", "Accepted", "Declined")
OPEN_STATUS = ("New", "In Review", "Responded", "Closed")


def clean(doc):
    if doc is None:
        return None
    return {k: v for k, v in doc.items() if k != "_id" and k not in ("idempotency_key", "payload_hash")}


def normalize(payload):
    if not isinstance(payload, dict) or any(key not in {"fullName", "email", "phone", "company", "notes", "items", "website"} for key in payload):
        raise ValueError("Invalid quotation fields.")
    # Honeypot; do not store spam content.
    if payload.get("website"):
        raise ValueError("Invalid quotation request.")
    fields = {}
    for key, maximum in (("fullName", 160), ("email", 254), ("phone", 40), ("company", 180), ("notes", 2000)):
        value = payload.get(key, "")
        if not isinstance(value, str) or len(value.strip()) > maximum:
            raise ValueError("Invalid customer information.")
        fields[key] = value.strip()
    if not all(fields[k] for k in ("fullName", "email", "phone", "company")):
        raise ValueError("Name, email, phone and company are required.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", fields["email"]):
        raise ValueError("Enter a valid email address.")
    rows = payload.get("items")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        raise ValueError("Please select 1–50 products.")
    ids = []
    for item in rows:
        if not isinstance(item, dict) or set(item) != {"id", "quantity"}:
            raise ValueError("Invalid selected product.")
        product_id, qty = item["id"], item["quantity"]
        if not isinstance(product_id, str) or not 1 <= len(product_id) <= 120 or isinstance(qty, bool) or not isinstance(qty, int) or not 1 <= qty <= 1000:
            raise ValueError("Invalid product or quantity.")
        ids.append(product_id)
    if len(set(ids)) != len(ids):
        raise ValueError("Combine duplicate products in the cart.")
    return {**fields, "items": sorted(rows, key=lambda item: item["id"])}


def validate(payload):
    normalized = normalize(payload)
    fields = {k: v for k, v in normalized.items() if k != "items"}
    rows = normalized["items"]
    ids = [item["id"] for item in rows]
    products = {x["id"]: x for x in db.products.find({"id": {"$in": ids}, "storefront_visible": {"$ne": False}})}
    if len(products) != len(ids):
        raise ValueError("A selected product is no longer available.")
    available = _availability_map(ids)
    lines = []
    for item in rows:
        product = products[item["id"]]
        in_stock = (available.get(item["id"], 0) > 0 if available is not None else (product.get("quantity") or 0) > 0)
        if identity_pending(product) or not in_stock:
            raise ValueError("A selected product is out of stock. Please update your cart.")
        try:
            price = _as_public_price(product.get("storefront_price"))
        except ValueError:
            price = None
        lines.append({"id": item["id"], "name": str(product.get("name", "")), "category": str(product.get("category", "")), "quantity": item["quantity"], "public_price_at_inquiry": price})
    return {**fields, "items": lines}


@public_bp.post("")
def submit_quotation():
    body = request.get_json(silent=True)
    key = request.headers.get("Idempotency-Key", "").strip()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{8,120}", key):
        return jsonify({"error": "Missing or invalid Idempotency-Key."}), 400
    try:
        normalized = normalize(body)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    # Hash only customer intent, never mutable prices, names or availability.
    digest = sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
    old = db.quotations.find_one({"idempotency_key": key})
    if old:
        # Also recover requests stored before normalized hashes were introduced.
        original = {k: old.get(k, "") for k in ("fullName", "email", "phone", "company", "notes")}
        original["items"] = [{"id": x["id"], "quantity": x["quantity"]} for x in sorted(old["items"], key=lambda item: item["id"])]
        if original != normalized:
            return jsonify({"error": "This request key has already been used."}), 409
        return jsonify({"reference": old["id"], "status": old["status"]}), 200
    try:
        data = validate(normalized)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    now = datetime.now(timezone.utc).isoformat()
    doc = {"id": "RFQ-" + uuid4().hex[:12].upper(), **data, "status": "New", "created_at": now, "updated_at": now, "idempotency_key": key, "payload_hash": digest}
    try:
        db.quotations.insert_one(doc)
    except DuplicateKeyError:
        old = db.quotations.find_one({"idempotency_key": key})
        if old and old.get("payload_hash") == digest:
            return jsonify({"reference": old["id"], "status": old["status"]}), 200
        return jsonify({"error": "Duplicate submission; please retry."}), 409
    return jsonify({"reference": doc["id"], "status": "New"}), 201


@staff_bp.get("")
@require_role("superadmin", "admin", "subadmin")
def list_quotations():
    docs = list(db.quotations.find({}, {"_id": 0, "payload_hash": 0, "idempotency_key": 0}).sort("created_at", -1).limit(200))
    response = jsonify(docs)
    response.headers["Cache-Control"] = "no-store"
    return response


class InquiryProblem(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


@staff_bp.errorhandler(InquiryProblem)
def inquiry_error(exc):
    return jsonify({"error": str(exc)}), exc.status


def transition(reference, status):
    actor = g.user["email"]
    now = datetime.now(timezone.utc).isoformat()

    def change(session):
        old = db.quotations.find_one({"id": reference}, session=session)
        if not old:
            raise InquiryProblem("Quotation not found.", 404)
        if old["status"] == status:
            return {"reference": reference, "status": status, "order_id": old.get("order_id")}
        if old["status"] not in OPEN_STATUS:
            raise InquiryProblem("Accepted and declined inquiries cannot be changed.")
        updates = {"status": status, "updated_at": now}
        if status == "Accepted":
            # Use the official Orders pricing policy (current internal catalog price).
            # No inventory reads/writes or reservations are performed here.
            products = {p["id"]: p for p in db.products.find(
                {"id": {"$in": [x["id"] for x in old["items"]]}}, session=session)}
            lines = []
            total = Decimal("0")
            for item in old["items"]:
                product = products.get(item["id"])
                if not product:
                    raise InquiryProblem("A requested product no longer exists.")
                if identity_pending(product):raise InquiryProblem(IDENTITY_REQUIRED)
                try:
                    price = None if product.get('price',0) is None else Decimal(str(product.get("price", 0)))
                    if price is not None and (not price.is_finite() or price < 0):
                        raise ValueError()
                    if price is not None:price = price.quantize(Decimal("0.01"))
                except (InvalidOperation, ValueError):
                    raise InquiryProblem("A requested product has an invalid order price.") from None
                subtotal = None if price is None else price * item["quantity"]
                total = None if total is None or subtotal is None else total + subtotal
                lines.append({"id": item["id"], "name": product["name"],
                              "unit": product.get("unit", "pcs"), "price": None if price is None else float(price),
                              "qty": item["quantity"], "lineTotal": None if subtotal is None else float(subtotal)})
            from routes.orders import _next_order_id
            order_id = _next_order_id()
            order = {"id": order_id, "source_inquiry_id": reference,
                     "client": old["fullName"], "email": old["email"],
                     "facility": old["company"], "phone": old["phone"],
                     "lines": lines, "total": None if total is None else float(total), "status": "Pending", "date": now,
                     "notes": ([{"text": old["notes"], "author": "customer", "at": old["created_at"]}]
                               if old.get("notes") else []),
                     "created_by": actor}
            db.orders.insert_one(order, session=session)
            updates.update(order_id=order_id, accepted_by=actor, accepted_at=now)
        elif status == "Declined":
            updates.update(declined_by=actor, declined_at=now)
        db.quotations.update_one({"id": reference}, {"$set": updates}, session=session)
        db.quotation_events.insert_one({"id": uuid4().hex, "reference": reference,
            "from": old["status"], "to": status, "actor_email": actor, "at": now,
            "order_id": updates.get("order_id")}, session=session)
        return {"reference": reference, "status": status, "order_id": updates.get("order_id")}

    # Transaction retry handles concurrent accept/decline and ambiguous commits.
    try:
        with db.client.start_session() as session:
            result = session.with_transaction(change)
    except DuplicateKeyError:
        # A concurrent acceptance may have committed the unique source link.
        existing = db.quotations.find_one({"id": reference})
        if status == "Accepted" and existing and existing.get("status") == "Accepted":
            result = {"reference": reference, "status": "Accepted", "order_id": existing["order_id"]}
        else:
            raise InquiryProblem("Inquiry changed concurrently; refresh and retry.") from None
    response = jsonify(result)
    response.headers["Cache-Control"] = "no-store"
    return response


@staff_bp.patch("/<reference>/status")
@require_role("superadmin", "subadmin")
def update_status(reference):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != {"status"} or body["status"] not in ALLOWED_STATUS:
        return jsonify({"error": "Invalid quotation status."}), 400
    return transition(reference, body["status"])


@staff_bp.post("/<reference>/accept")
@require_role("superadmin", "subadmin")
def accept(reference):
    return transition(reference, "Accepted")


@staff_bp.post("/<reference>/decline")
@require_role("superadmin", "subadmin")
def decline(reference):
    return transition(reference, "Declined")
