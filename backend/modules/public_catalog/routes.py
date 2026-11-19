"""Public catalog and audited staff-facing storefront settings.

Separate from employee product/inventory routes. Never returns batch, staff,
invoice, reserved quantity, or cost records to anonymous customers.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, g, jsonify, request

from config import Config
from extensions import db
from routes.products import _valid_product_image
from utils.security import require_role
from modules.product_metadata import public_metadata, identity_pending

bp = Blueprint("public_catalog", __name__, url_prefix="/api/public/products")
staff_bp = Blueprint("staff_catalog", __name__, url_prefix="/api/products")


def _as_public_price(value):
    """Float public currency amount to two decimal places, or null if unset."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Public price must be a non-negative amount or null.")
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Public price must be a non-negative amount or null.") from None
    if not decimal_value.is_finite() or decimal_value < 0 or decimal_value > 999999999:
        raise ValueError("Public price must be between 0 and 999999999.")
    if decimal_value.as_tuple().exponent < -2:
        raise ValueError("Public price must have at most two decimal places.")
    return float(decimal_value)


def _visible(product):
    # Existing products without this field should also publish automatically.
    return product.get("storefront_visible", True) is not False


def _availability_map(product_ids):
    """Find eligible unreserved stock for only the requested page/product.

    Uses the same batch eligibility rules as FEFO allocation. Never reveals
    quantities, lot details, or inventory reservations to visitors.
    """
    if not Config.BATCH_MODE:
        # Only used for installations deliberately operating in legacy mode.
        return None
    if not product_ids:
        return {}
    today = date.today().isoformat()
    eligible = db.inventory_batches.find(
        {"product_id": {"$in": product_ids},
         "condition": "available", "unverified": False,
         "expires_on": {"$gte": today}},
        {"_id": 0, "product_id": 1, "on_hand": 1, "reserved": 1},
    )
    available = {}
    for batch in eligible:
        product_id = batch.get("product_id")
        if not product_id:
            continue
        units = max(0, int(batch.get("on_hand") or 0) - int(batch.get("reserved") or 0))
        available[product_id] = available.get(product_id, 0) + units
    return available


def _safe_public_product(product, available):
    details = public_metadata(product)
    image = details['imageUrls'][0] if details['imageUrls'] else None
    public_price = product.get("storefront_price")
    if identity_pending(product):public_price=None
    try:
        public_price = _as_public_price(public_price)
    except ValueError:
        public_price = None
    return {
        "id": str(product["id"]),
        "slug": str(product["id"]),  # Stable, non-colliding product identifier.
        "name": str(product.get("name") or ""),
        "description": str(product.get("description") or ""),
        "category": str(product.get("category") or ""),
        "brand": str(product.get("brand") or product.get("manufacturer") or ""),
        "manufacturer": str(product.get("manufacturer") or "") if 'brand' in product else '',
        "model": str(product.get('model') or ''),
        "imageUrl": image or None,
        **details,
        "publicPrice": public_price,
        "inStock": not identity_pending(product) and (available.get(product["id"], 0) > 0 if available is not None
                    else (product.get("quantity") or 0) > 0),
        "publishedAt": str(product.get("created_at") or ""),
    }


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("")
def list_public_products():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 100))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid pagination."}), 400
    if page < 1 or not 1 <= limit <= 200 or page > 10000:
        return jsonify({"error": "Page must be positive and limit must be 1–200."}), 400
    query = {"storefront_visible": {"$ne": False}}
    total = db.products.count_documents(query)
    documents = db.products.find(query, {"_id": 0, "id": 1, "name": 1,
        "description": 1, "category": 1, "brand": 1, "manufacturer": 1, "model": 1, "image": 1,
        "quantity": 1, "storefront_price": 1, "created_at": 1,
        "images": 1, "key_features": 1, "specifications": 1, "identity_status":1, "sku":1, "unit":1})
    products = list(documents.sort("id", 1).skip((page-1)*limit).limit(limit))
    available = _availability_map([p["id"] for p in products])
    response = jsonify({"products": [_safe_public_product(p, available) for p in products],
                        "page": page, "pageSize": limit, "total": total,
                        "hasMore": page * limit < total})
    return _no_store(response)


@bp.get("/<product_id>")
def get_public_product(product_id):
    product = db.products.find_one({"id": product_id, "storefront_visible": {"$ne": False}})
    if not product:
        return jsonify({"error": "Product not found."}), 404
    return _no_store(jsonify(_safe_public_product(product, _availability_map([product_id]))))


@staff_bp.patch("/<product_id>/storefront")
@require_role("superadmin")
def update_storefront_settings(product_id):
    """Only Superadmin can publish/hide products or change public prices.

    This does not mutate invoice selling prices or any batch/stock field.
    """
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object required."}), 400
    if not body or any(k not in {"visible", "publicPrice"} for k in body):
        return jsonify({"error": "Only visible and publicPrice may be updated."}), 400
    updates = {}
    if "visible" in body:
        if not isinstance(body["visible"], bool):
            return jsonify({"error": "visible must be true or false."}), 400
        updates["storefront_visible"] = body["visible"]
    if "publicPrice" in body:
        try:
            updates["storefront_price"] = _as_public_price(body["publicPrice"])
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    now = datetime.now(timezone.utc).isoformat()

    product=db.products.find_one({'id':product_id})
    if product and identity_pending(product) and updates.get('storefront_price') is not None:
        return jsonify(error='Confirm the genuine SKU and selling unit before approving a public price.'),409

    def change(session):
        old = db.products.find_one({"id": product_id}, session=session)
        if not old:
            return None
        before = {field: old.get(field, True if field == "storefront_visible" else None)
                  for field in updates}
        result = db.products.update_one({"id": product_id}, {"$set": updates}, session=session)
        if result.matched_count != 1:
            return None
        db.catalog_events.insert_one({"id": uuid4().hex, "product_id": product_id,
            "action": "storefront_settings", "before": before, "after": updates,
            "actor_email": g.user["email"], "at": now}, session=session)
        return db.products.find_one({"id": product_id}, session=session)

    with db.client.start_session() as session:
        updated = session.with_transaction(change)
    if not updated:
        return jsonify({"error": "Product not found."}), 404
    return _no_store(jsonify({"id": product_id,
        "visible": _visible(updated),
        "publicPrice": updated.get("storefront_price")}))
