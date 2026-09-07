from flask import Blueprint, request, jsonify

from extensions import db
from utils.security import require_admin

bp = Blueprint("products", __name__, url_prefix="/api/products")

REQUIRED_FIELDS = ["id", "name", "cat", "tag", "brand", "price", "unit", "stock"]


def _serialize(p: dict) -> dict:
    p = dict(p)
    p.pop("_id", None)
    return p


@bp.get("")
def list_products():
    """Public. Supports ?cat=<category>&q=<search text>."""
    query = {}
    cat = request.args.get("cat")
    if cat and cat != "all":
        query["cat"] = cat

    q = (request.args.get("q") or "").strip()
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"id": {"$regex": q, "$options": "i"}},
        ]

    products = [_serialize(p) for p in db.products.find(query).sort("id", 1)]
    return jsonify(products)


@bp.get("/<product_id>")
def get_product(product_id):
    p = db.products.find_one({"id": product_id})
    if not p:
        return jsonify({"error": "Product not found."}), 404
    return jsonify(_serialize(p))


@bp.post("")
@require_admin
def create_product():
    data = request.get_json(silent=True) or {}
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    if db.products.find_one({"id": data["id"]}):
        return jsonify({"error": f"Product {data['id']} already exists."}), 409

    doc = {f: data[f] for f in REQUIRED_FIELDS}
    try:
        doc["price"] = float(doc["price"])
    except (TypeError, ValueError):
        return jsonify({"error": "price must be a number."}), 400

    db.products.insert_one(doc)
    return jsonify(_serialize(doc)), 201


@bp.put("/<product_id>")
@require_admin
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    updates = {f: data[f] for f in REQUIRED_FIELDS if f in data}
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
@require_admin
def delete_product(product_id):
    result = db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"deleted": product_id})
