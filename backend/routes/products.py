"""
Product catalog. Superadmin is the only role that can create a product.
Quantity changes only through /api/inventory so stock changes stay audited.

Phase 3 adds optional pagination and safer search without changing the
existing response shape. When page/limit are omitted, existing frontend
behavior remains unchanged.
"""
from datetime import datetime, timezone
import math
import re
import hashlib
import json
from uuid import uuid4

from flask import Blueprint, request, jsonify, g, make_response
from pymongo.errors import DuplicateKeyError

from config import Config
from extensions import db
from utils.security import require_role
from realtime import emit_inventory_log
from modules.product_metadata import metadata, canonical_sku, valid_image as _valid_product_image, identifier_keys, PENDING_UNIT, TEMP_ID_PREFIX

bp = Blueprint("products", __name__, url_prefix="/api/products")

REQUIRED_FIELDS = ["id", "name", "description", "category", "unit", "quantity"]
OPTIONAL_FIELDS = ["price", "manufacturer", "brand", "model", "image", "images", "key_features", "specifications"]


@bp.before_request
def bounded_metadata_request():
    if request.method in ('POST','PUT') and request.content_length and request.content_length > 3000000:
        return jsonify(error='Product metadata request exceeds 3 MB.'), 413



def _status(p: dict) -> str:
    qty = p.get("quantity", 0)
    if qty <= 0:
        return "out-of-stock"
    baseline = p.get("baseline_qty", 0)
    if baseline > 0 and qty * 10 <= baseline * 3:
        return "low-stock"
    return "in-stock"


def _serialize(p: dict) -> dict:
    p = dict(p)
    p.pop("_id", None)
    p["status"] = _status(p)
    return p


def _optional_pagination():
    """Return (page, limit) only when the caller explicitly requests it."""
    if "page" not in request.args and "limit" not in request.args:
        return None, None

    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = max(1, int(request.args.get("limit", 50)))
    except (TypeError, ValueError):
        return "error", "error"

    return page, min(limit, Config.API_MAX_PAGE_SIZE)


def _json_list(items, total=None, page=None, limit=None):
    response = make_response(jsonify(items))
    if total is not None:
        response.headers["X-Total-Count"] = str(total)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(limit)
    return response


@bp.get("")
@require_role()
def list_products():
    """Supports ?category=&q=&page=&limit=."""
    query = {}
    category = request.args.get("category")
    if category and category != "all":
        query["category"] = category

    q = (request.args.get("q") or "").strip()
    if q:
        safe_q = re.escape(q)
        query["$or"] = [
            {"name": {"$regex": safe_q, "$options": "i"}},
            # Product IDs normally behave like prefixes; anchoring allows
            # MongoDB to use the ID index more effectively.
            {"id": {"$regex": f"^{safe_q}", "$options": "i"}},
            {"sku": {"$regex": f"^{safe_q}", "$options": "i"}},
        ]

    page, limit = _optional_pagination()
    if page == "error":
        return jsonify({"error": "page and limit must be whole numbers."}), 400

    cursor = db.products.find(query).sort("id", 1)

    if page is None:
        return jsonify([_serialize(p) for p in cursor])

    total = db.products.count_documents(query)
    cursor = cursor.skip((page - 1) * limit).limit(limit)
    return _json_list(
        [_serialize(p) for p in cursor],
        total=total,
        page=page,
        limit=limit,
    )


@bp.get("/<product_id>")
@require_role()
def get_product(product_id):
    p = db.products.find_one({"id": product_id})
    if not p:
        return jsonify({"error": "Product not found."}), 404
    return jsonify(_serialize(p))


class ProductProblem(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def product_image_state(product):
    """Comparison token for gallery-only changes; never includes stock/prices."""
    return hashlib.sha256(json.dumps({key:product.get(key) for key in ('image','images')},
        sort_keys=True,separators=(',',':')).encode()).hexdigest()


def update_product_images(product_id, data, actor_email, expected_state=None, source_review=None, session=None):
    """Existing product service: validated, audited, idempotent image-only update.

    Optional source evidence is stored on the audit event, preserving historical
    import metadata and every product field except image/images.
    """
    if not isinstance(data,dict) or not data or set(data)-{'image','images'}:
        raise ProductProblem('Image-only updates accept image/images fields only.')
    def change(tx):
        actor=db.users.find_one({'email':actor_email},session=tx)
        if not actor or actor.get('role') not in ('superadmin','subadmin') or actor.get('is_active') is False or actor.get('disabled'):
            raise ProductProblem('An active authorized product editor is required.',403)
        old=db.products.find_one({'id':product_id},session=tx)
        if not old:raise ProductProblem('Product not found.',404)
        try:updates=metadata(data,old)
        except ValueError as exc:raise ProductProblem(str(exc)) from None
        before=product_image_state(old)
        if old.get('image')==updates['image'] and old.get('images')==updates['images']:
            return {'product':old,'changed':False,'event_id':None}
        if expected_state is not None and before!=expected_state:
            raise ProductProblem('The gallery changed after source review; stop and review it again.',409)
        db.products.update_one({'_id':old['_id']},{'$set':updates},session=tx)
        event_id=uuid4().hex
        event={'id':event_id,'product_id':product_id,'action':'product_images_updated',
            'actor_email':actor_email,'at':datetime.now(timezone.utc).isoformat(),
            'before_image_hash':before,'after_image_hash':product_image_state({**old,**updates}),
            'previous_image_count':len(old.get('images') or ([old['image']] if old.get('image') else [])),
            'image_count':len(updates['images'])}
        if source_review is not None:event['source_review']=source_review
        db.catalog_events.insert_one(event,session=tx)
        return {'product':{**old,**updates},'changed':True,'event_id':event_id}
    if session is not None:return change(session)
    with db.client.start_session() as tx:return tx.with_transaction(change)


def prepare_product(data, provisional=False):
    """One validation path for ordinary creation and approved brochure imports."""
    if not isinstance(data, dict):
        raise ProductProblem('A JSON object is required.')
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ProductProblem(f"Missing fields: {', '.join(missing)}")

    doc = {f: data[f] for f in REQUIRED_FIELDS}
    for f in OPTIONAL_FIELDS:
        doc[f] = data.get(f, (None if provisional else 0) if f == "price" else [] if f in ('images','key_features','specifications') else '')

    try:
        doc.update(metadata(data))
        if not doc['images'] and doc.get('image'):
            doc['images'] = [doc['image']]
    except ValueError as exc:
        raise ProductProblem(str(exc)) from None

    try:
        doc["quantity"] = int(doc["quantity"])
        doc["price"] = None if provisional and doc['price'] is None else float(doc["price"])
    except (TypeError, ValueError):
        raise ProductProblem('quantity and price must be numbers.')

    if doc['price'] is not None and (not math.isfinite(doc['price']) or doc['price'] < 0):
        raise ProductProblem('price must be a finite non-negative amount.')
    if not _valid_product_image(doc["image"]):
        raise ProductProblem('Product image must be a valid PNG, JPEG or WebP under 200 KB.')
    if Config.BATCH_MODE and doc['quantity'] != 0:
        raise ProductProblem('Batch mode requires new products to start with zero stock. Use /api/v2/inventory/batches/receive.', 409)
    if doc["quantity"] < 0:
        raise ProductProblem('quantity cannot be negative.')

    if provisional:
        if not doc['id'].startswith(TEMP_ID_PREFIX) or doc['unit'] != PENDING_UNIT or doc['quantity'] != 0 or doc['price'] is not None:
            raise ProductProblem('Provisional PDF products require a marked internal ID, pending unit, zero stock and an unset price.')
        doc.update(identity_status='provisional', sku='')
    elif doc['id'].upper().startswith(TEMP_ID_PREFIX) or doc['unit'] == PENDING_UNIT:
        raise ProductProblem('Temporary PDF identifiers and pending units are reserved for guarded source-product creation.')

    doc["baseline_qty"] = doc["quantity"]
    # Publication is metadata only. Physical stock remains zero until received.
    doc["storefront_visible"] = True
    doc["storefront_price"] = None
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc['_sku_key'] = canonical_sku(doc['id'])
    return doc


def insert_product_document(doc, session=None):
    """Shared persistence path. The caller owns any import transaction/audit."""
    # Existing records need no backfill. New records also have an atomic unique
    # comparison-key index, including ordinary product creation and imports.
    if any(identifier_keys(p) & identifier_keys(doc) for p in db.products.find({}, {'id':1,'sku':1}, session=session)):
        raise DuplicateKeyError('Product identifier already exists.')
    db.products.insert_one(doc, session=session)


@bp.post("")
@require_role("superadmin", "subadmin")
def create_product():
    try:
        doc = prepare_product(request.get_json(silent=True) or {})
    except ProductProblem as exc:
        return jsonify(error=str(exc)), exc.status

    try:
        insert_product_document(doc)
    except DuplicateKeyError:
        return jsonify({"error": f"Product {doc['id']} already exists."}), 409

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
@require_role("superadmin", "subadmin")
def update_product(product_id):
    """Edits product metadata. Quantity only changes through /api/inventory."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error='A JSON object is required.'), 400
    if data and set(data)<= {'image','images'}:
        try:
            result=update_product_images(product_id,data,g.user['email'])
            return jsonify(_serialize(result['product']))
        except ProductProblem as exc:
            return jsonify(error=str(exc)),exc.status
    existing = db.products.find_one({'id': product_id})
    if not existing:
        return jsonify(error='Product not found.'), 404
    if 'identity_status' in data:
        return jsonify(error='Identity status is server-controlled. Confirm the genuine SKU and unit in this product editor.'), 400
    editable = [f for f in REQUIRED_FIELDS + OPTIONAL_FIELDS if f != "quantity"]
    updates = {f: data[f] for f in editable if f in data}
    try:
        updates.update(metadata(data, existing))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    if Config.BATCH_MODE and 'id' in updates and updates['id'] != product_id:
        return jsonify({'error': 'Product identifiers cannot be changed in batch mode.'}), 409
    if existing.get('identity_status') and updates.get('id',product_id) != product_id:
        return jsonify(error='The internal product ID and shareable URL remain stable; enter the genuine SKU separately.'), 409

    confirming = data.get('confirm_identity') is True
    if confirming:
        sku = data.get('sku', '')
        unit = updates.get('unit', existing.get('unit',''))
        note = data.get('identity_review_note','')
        if existing.get('identity_status') != 'provisional':
            return jsonify(error='This identity is already confirmed or is a legacy SKU. Refresh the product.'), 409
        if not isinstance(sku,str) or not 1<=len(sku.strip())<=80 or canonical_sku(sku).startswith(TEMP_ID_PREFIX.lower()):
            return jsonify(error='Enter the genuine staff-confirmed SKU, not the temporary internal ID.'), 400
        if not unit or canonical_sku(unit) in {canonical_sku(PENDING_UNIT),'pending','unknown','tbd','unconfirmed'} or not isinstance(note,str) or not 5<=len(note.strip())<=2000:
            return jsonify(error='Confirm the genuine selling unit and record the identity evidence/review note.'), 400
        updates.update(sku=sku.strip(),identity_status='confirmed',
            identity_confirmed_by=g.user['email'],identity_confirmed_at=datetime.now(timezone.utc).isoformat(),
            identity_review_note=note.strip())
    elif 'sku' in data or 'confirm_identity' in data:
        return jsonify(error='SKU confirmation requires the explicit confirmation checkbox and review note.'), 400
    if existing.get('identity_status') != 'provisional' and 'unit' in updates and canonical_sku(updates['unit']) == canonical_sku(PENDING_UNIT):
        return jsonify(error='A confirmed unit cannot be replaced with the pending-unit marker.'), 400

    if "price" in updates:
        try:
            updates["price"] = None if existing.get('identity_status') and updates['price'] is None else float(updates["price"])
            if updates['price'] is not None and (not math.isfinite(updates['price']) or updates['price'] < 0):
                raise ValueError()
        except (TypeError, ValueError):
            return jsonify({"error": "price must be a number."}), 400
        if existing.get('identity_status') == 'provisional' and not confirming and updates['price'] is not None:
            return jsonify(error='Confirm the genuine SKU and selling unit before entering a catalog price.'),409

    if "image" in updates and not _valid_product_image(updates["image"]):
        return jsonify({"error": "Product image must be a valid PNG, JPEG or WebP under 200 KB."}), 400

    if not updates:
        return jsonify({"error": "No valid fields to update."}), 400

    if 'id' in updates or confirming:
        updates['_sku_key'] = canonical_sku(updates.get('sku') or existing.get('sku') or updates.get('id', product_id))
        proposed={**existing,**updates}
        if any(identifier_keys(p) & identifier_keys(proposed) for p in db.products.find({'id':{'$ne':product_id}}, {'id':1,'sku':1})):
            return jsonify(error='That product identifier already exists.'), 409

    try:
        if confirming:
            def confirm(session):
                current=db.products.find_one({'id':product_id},session=session)
                if not current or current.get('identity_status') != 'provisional':
                    raise ProductProblem('The product identity changed; refresh and review it again.',409)
                if any(identifier_keys(p) & identifier_keys({**current,**updates}) for p in db.products.find({'id':{'$ne':product_id}}, {'id':1,'sku':1},session=session)):
                    raise DuplicateKeyError('SKU already exists.')
                db.products.update_one({'id':product_id,'identity_status':'provisional'},{'$set':updates},session=session)
                db.catalog_events.insert_one({'id':uuid4().hex,'product_id':product_id,'action':'product_identity_confirmed',
                    'sku':updates['sku'],'unit':updates.get('unit',current['unit']),
                    'actor_email':g.user['email'],'note':updates['identity_review_note'],'at':updates['identity_confirmed_at']},session=session)
            with db.client.start_session() as session:session.with_transaction(confirm)
            return jsonify(_serialize(db.products.find_one({'id':product_id})))
        query={'id':product_id}
        if existing.get('identity_status') == 'provisional':query['identity_status']='provisional'
        result = db.products.update_one(query, {"$set": updates})
    except ProductProblem as exc:
        return jsonify(error=str(exc)),exc.status
    except DuplicateKeyError:
        return jsonify({"error": f"Product identifier {updates.get('sku') or updates.get('id', product_id)} already exists."}), 409

    if result.matched_count == 0:
        return jsonify({"error": "Product not found."}), 404

    lookup_id = updates.get("id", product_id)
    return jsonify(_serialize(db.products.find_one({"id": lookup_id})))


@bp.delete("/<product_id>")
@require_role("superadmin")
def delete_product(product_id):
    result = db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Product not found."}), 404
    return jsonify({"deleted": product_id})
