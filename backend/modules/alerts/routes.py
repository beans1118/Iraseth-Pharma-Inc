"""Read-only inventory watchlist. No automatic adjustments or stock writes."""
from datetime import date, datetime, timedelta, timezone
from flask import Blueprint, jsonify, request, g
from extensions import db
from utils.security import require_role

bp = Blueprint('alerts_api', __name__, url_prefix='/api/v2/alerts')


def compute_watchlist(products, batches, today, days, threshold):
    """Pure function so expiry/stock rules can be tested without database access."""
    end = (date.fromisoformat(today) + timedelta(days=days)).isoformat()
    by_product = {}
    expiring = []
    expired = []
    restricted = []
    for b in batches:
        pid = str(b.get('product_id') or '')
        on_hand = max(0, b.get('on_hand') or 0)
        reserved = max(0, b.get('reserved') or 0)
        expires = b.get('expires_on') or ''
        condition = b.get('condition')
        unverified = b.get('unverified') is True
        if not on_hand:
            continue
        item = {'batch_id': str(b.get('id') or ''), 'product_id': pid, 'lot': str(b.get('lot') or ''),
                'expires_on': expires, 'on_hand': on_hand, 'reserved': reserved,
                'condition': condition or 'unknown'}
        if expires and expires < today:
            expired.append(item)
        elif condition != 'available' or unverified:
            restricted.append(item)
        elif today <= expires <= end:
            expiring.append(item)
        if condition == 'available' and not unverified and expires >= today:
            by_product[pid] = by_product.get(pid, 0) + max(0, on_hand - reserved)
    low_stock = []
    stockouts = []
    all_products = []
    for p in products:
        pid = str(p.get('id') or '')
        eligible = by_product.get(pid, 0)
        configured = p.get('min_stock_threshold')
        effective = configured if isinstance(configured, int) and not isinstance(configured, bool) and configured >= 0 else threshold
        item = {'product_id': pid, 'product_name': p.get('name') or pid,
                'category': p.get('category') or '', 'unit': p.get('unit') or '',
                'available': eligible, 'threshold': effective, 'custom_threshold': configured is not None}
        all_products.append(item)
        if eligible <= 0:
            stockouts.append(item)
        elif eligible <= effective:
            low_stock.append(item)
    expiring.sort(key=lambda b: (b['expires_on'],b['product_id'],b['lot']))
    expired.sort(key=lambda b: (b['expires_on'],b['product_id'],b['lot']))
    low_stock.sort(key=lambda p: (p['available'],p['product_name']))
    stockouts.sort(key=lambda p: p['product_name'])
    all_products.sort(key=lambda p: p['product_name'])
    return {'all_products':all_products,'low_stock':low_stock,'stockouts':stockouts,'expiring_batches':expiring,
            'expired_batches':expired,'restricted_batches':restricted}


@bp.get('/inventory')
@require_role('superadmin','admin','subadmin')
def inventory_alerts():
    try:
        days = int(request.args.get('days','30'))
        threshold = int(request.args.get('threshold','10'))
    except (TypeError, ValueError):
        return jsonify({'error':'days and threshold must be whole numbers.'}),400
    if days not in (30,60,90) or threshold < 0 or threshold > 100000:
        return jsonify({'error':'days must be 30, 60, or 90; threshold must be from 0 to 100000.'}),400
    today = date.today().isoformat()
    result = compute_watchlist(
        list(db.products.find({}, {'_id':0,'id':1,'name':1,'unit':1,'category':1,'min_stock_threshold':1})),
        list(db.inventory_batches.find({}, {'_id':0,'id':1,'product_id':1,'lot':1,'expires_on':1,
                                            'on_hand':1,'reserved':1,'condition':1,'unverified':1})),
        today, days, threshold)
    return jsonify({**result,'as_of_utc':datetime.now(timezone.utc).isoformat(),
                    'expiry_window_days':days,'global_preview_threshold':threshold,
                    'note':'Read-only review signals. Per-product thresholds override the global fallback in each product’s stored unit; no purchasing or stock changes occur. Expiry classification uses local server date.'})


@bp.patch('/products/<product_id>/threshold')
@require_role('superadmin')
def set_product_threshold(product_id):
    """Edit catalog alert policy only; never mutate physical inventory."""
    if not product_id or len(product_id) > 120:
        return jsonify({'error': 'Invalid product ID.'}), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or 'threshold' not in data:
        return jsonify({'error': 'Provide threshold (0–100000), or null to use the fallback.'}), 400
    value = data['threshold']
    if value is not None and (type(value) is not int or not 0 <= value <= 100000):
        return jsonify({'error': 'Threshold must be a whole number from 0 to 100000, or null.'}), 400
    from pymongo import ReturnDocument
    change = {'$unset': {'min_stock_threshold': ''}} if value is None else {'$set': {'min_stock_threshold': value}}
    with db.client.start_session() as session:
        with session.start_transaction():
            result = db.products.find_one_and_update({'id': product_id}, change,
                       projection={'_id': 0, 'id': 1, 'min_stock_threshold': 1},
                       return_document=ReturnDocument.AFTER, session=session)
            if result is None:
                return jsonify({'error': 'Product not found.'}), 404
            db.inventory_logs.insert_one({'product_id': product_id, 'action': 'alert_threshold',
                                          'threshold': value, 'actor_email': g.user['email'],
                                          'at': datetime.now(timezone.utc).isoformat(),
                                          'note': 'Alert policy updated; no stock changed.'},session=session)
    return jsonify({'product_id': product_id, 'threshold': value})
