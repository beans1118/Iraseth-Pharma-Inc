"""Staff invoices: a financial document ledger, NEVER a stock mutation endpoint."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from uuid import uuid4
from flask import Blueprint, jsonify, request, g
from pymongo.errors import DuplicateKeyError
from extensions import db
from utils.security import require_role

bp = Blueprint('invoice_api', __name__, url_prefix='/api/v2/invoices')
ROLES = ('superadmin', 'admin', 'subadmin')
MONEY = Decimal('0.01')

def clean(doc):
    if doc is None: return None
    doc = dict(doc)
    doc.pop('_id', None)
    return doc

def now():
    return datetime.now(timezone.utc).isoformat()

def amount(value):
    if isinstance(value, bool): raise ValueError('Prices must be numeric.')
    try: result = Decimal(str(value))
    except (TypeError, InvalidOperation): raise ValueError('Invalid price.')
    if not result.is_finite() or result < 0 or result > Decimal('99999999.99') or result.as_tuple().exponent < -2:
        raise ValueError('Price must be non-negative and have at most two decimals.')
    return result.quantize(MONEY, rounding=ROUND_HALF_UP)

def validate(payload):
    source = payload.get('order_id')
    if source and not isinstance(source, str): raise ValueError('Invalid order reference.')
    order = db.orders.find_one({'id': source}) if source else None
    if source and not order: raise ValueError('Order not found.')
    client = str((order or {}).get('client') or payload.get('client') or '').strip()
    email = str((order or {}).get('email') or payload.get('email') or '').strip()
    facility = str((order or {}).get('facility') or payload.get('facility') or '').strip()
    if not client or not email or not facility or len(client)>160 or len(email)>254 or len(facility)>160:
        raise ValueError('Customer, email and facility are required (within length limits).')
    raw = payload.get('lines')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 100: raise ValueError('Provide 1–100 invoice lines.')
    if order:
        order_lines = order.get('lines') or []
        if len(raw) != len(order_lines): raise ValueError('Invoice lines must match the selected order.')
        for item, original in zip(raw,order_lines):
            if str(item.get('id')) != str(original.get('id')) or item.get('qty') != original.get('qty'):
                raise ValueError('Invoice products and quantities must match the selected order.')
    ids = [line.get('id') for line in raw if isinstance(line,dict)]
    if len(ids)!=len(raw) or any(not isinstance(x,str) or not x for x in ids): raise ValueError('Invalid invoice product.')
    if len(ids)!=len(set(ids)): raise ValueError('Combine repeated products into one line.')
    catalog = {p['id']:p for p in db.products.find({'id':{'$in':ids}})}
    if len(catalog)!=len(ids): raise ValueError('One or more products no longer exist.')
    lines=[]; total=Decimal('0.00')
    for row in raw:
        qty=row.get('qty')
        if isinstance(qty,bool) or not isinstance(qty,int) or qty<=0 or qty>1000000: raise ValueError('Quantity must be a positive whole number.')
        price=amount(row.get('price'))
        p=catalog[row['id']]
        subtotal=price*qty
        if subtotal>Decimal('999999999.99'): raise ValueError('Line amount too high.')
        total+=subtotal
        lines.append({'id':p['id'],'name':p['name'],'unit':p.get('unit',''), 'qty':qty,'price':str(price),'subtotal':str(subtotal)})
    if total>Decimal('999999999.99'): raise ValueError('Invoice total too high.')
    return {'order_id':source or None, 'client':client, 'email':email,'facility':facility,'lines':lines,'total':str(total),'currency':'PHP'}

def audit(invoice_id, event, actor, session=None):
    db.invoice_events.insert_one({'id':uuid4().hex,'invoice_id':invoice_id,'event':event,'actor_email':actor,'at':now()},session=session)

@bp.get('')
@require_role(*ROLES)
def list_invoices():
    return jsonify([clean(x) for x in db.invoices.find().sort('created_at',-1).limit(250)])

@bp.get('/transactions')
@require_role(*ROLES)
def transactions():
    return jsonify([clean(x) for x in db.invoice_events.find().sort('at',-1).limit(250)])

@bp.get('/<invoice_id>')
@require_role(*ROLES)
def get_invoice(invoice_id):
    doc=db.invoices.find_one({'id':invoice_id})
    return jsonify(clean(doc)) if doc else (jsonify({'error':'Invoice not found.'}),404)

@bp.post('')
@require_role("superadmin", "subadmin")
def create_invoice():
    payload=request.get_json(silent=True)
    if not isinstance(payload,dict): return jsonify({'error':'JSON object required.'}),400
    try: fields=validate(payload)
    except ValueError as e: return jsonify({'error':str(e)}),400
    key=request.headers.get('Idempotency-Key','').strip()
    if not 8<=len(key)<=120 or not re.fullmatch(r'[A-Za-z0-9_-]+',key):
        return jsonify({'error':'Valid Idempotency-Key required (8–120 letters, digits, underscore or dash).'}),400
    # Idempotency is scoped to staff account; payload identity is bound to the key.
    import hashlib, json
    digest=hashlib.sha256(json.dumps(fields,sort_keys=True).encode()).hexdigest()
    existing=db.invoices.find_one({'actor_email':g.user['email'],'idempotency_key':key})
    if existing:
        if existing.get('payload_hash')!=digest: return jsonify({'error':'Idempotency key already used for another invoice.'}),409
        return jsonify(clean(existing)),200
    doc={'id':'INV-'+uuid4().hex[:12].upper(),**fields,'status':'Draft','created_at':now(), 'updated_at':now(), 'actor_email':g.user['email'],'idempotency_key':key,'payload_hash':digest}
    try:
        with db.client.start_session() as session:
            with session.start_transaction():
                db.invoices.insert_one(doc,session=session)
                audit(doc['id'],'created',g.user['email'],session=session)
    except DuplicateKeyError:
        existing=db.invoices.find_one({'actor_email':g.user['email'],'idempotency_key':key})
        if existing and existing.get('payload_hash')==digest: return jsonify(clean(existing)),200
        return jsonify({'error':'Duplicate invoice request; retry with a new key.'}),409
    return jsonify(clean(doc)),201

@bp.post('/<invoice_id>/issue')
@require_role("superadmin", "subadmin")
def issue_invoice(invoice_id):
    with db.client.start_session() as session:
        with session.start_transaction():
            doc=db.invoices.find_one_and_update({'id':invoice_id,'status':'Draft'},{'$set':{'status':'Issued','updated_at':now()}},session=session,return_document=True)
            if doc:audit(invoice_id,'issued',g.user['email'],session=session)
    if not doc:return jsonify({'error':'Invoice not found or no longer a draft.'}),409
    return jsonify(clean(doc))

@bp.post('/<invoice_id>/void')
@require_role('superadmin')
def void_invoice(invoice_id):
    with db.client.start_session() as session:
        with session.start_transaction():
            doc=db.invoices.find_one_and_update({'id':invoice_id,'status':{'$in':['Draft','Issued']}},{'$set':{'status':'Voided','updated_at':now()}},session=session,return_document=True)
            if doc:audit(invoice_id,'voided',g.user['email'],session=session)
    if not doc:return jsonify({'error':'Invoice not found or already voided.'}),409
    return jsonify(clean(doc))
