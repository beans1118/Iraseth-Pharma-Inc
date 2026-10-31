"""Opt-in batch inventory API. Not exposed unless BATCH_MODE=enabled."""
from flask import Blueprint, jsonify, request, g
from config import Config
from extensions import db
from utils.security import require_role
from . import service as svc

bp = Blueprint('batch_inventory', __name__, url_prefix='/api/v2/inventory')


def enabled():
    if not Config.BATCH_MODE:
        return jsonify({'error': 'Batch mode disabled. Complete migration and reconciliation first.'}), 503


@bp.errorhandler(svc.InventoryProblem)
def problem(exc):
    return jsonify({'error': str(exc)}), exc.status


def data():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise svc.InventoryProblem('JSON object required.', 400)
    return value


def key():
    return request.headers.get('Idempotency-Key', '')


@bp.get('/batches')
@require_role()
def list_batches():
    if (blocked := enabled()) is not None:
        return blocked
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, max(1, int(request.args.get('limit', 25))))
    except ValueError:
        return jsonify({'error': 'Invalid pagination.'}), 400
    query = {}
    if request.args.get('product_id'):
        query['product_id'] = request.args['product_id']
    total = db.inventory_batches.count_documents(query)
    result = [svc.clean(b) for b in db.inventory_batches.find(query).sort([
        ('expires_on', 1), ('id', 1)]).skip((page - 1)*limit).limit(limit)]
    return jsonify({'items': result, 'total': total, 'page': page})


@bp.post('/batches/receive')
@require_role('superadmin', 'subadmin')
def receive():
    if (blocked := enabled()) is not None:
        return blocked
    d = data()
    return jsonify(svc.receive(d.get('product_id'), d.get('lot'), d.get('expires_on'),
        d.get('qty'), g.user['email'], key(), d.get('condition', 'available'),
        d.get('reference', 'manual receipt'))), 201


@bp.post('/release')
@require_role('superadmin', 'subadmin')
def release():
    if (blocked := enabled()) is not None:
        return blocked
    d = data()
    return jsonify(svc.manual_release(d.get('product_id'), d.get('qty'),
        g.user['email'], key(), d.get('reason')))


@bp.post('/adjustments')
@require_role('subadmin')
def adjustment_request():
    if (blocked := enabled()) is not None:
        return blocked
    d = data()
    return jsonify(svc.request_adjustment(d.get('batch_id'), d.get('delta'),
        d.get('reason'), g.user['email'])), 201


@bp.post('/adjustments/<adjustment_id>/decision')
@require_role('superadmin')
def adjustment_decision(adjustment_id):
    if (blocked := enabled()) is not None:
        return blocked
    d = data()
    if type(d.get('approve')) is not bool:
        raise svc.InventoryProblem('approve must be true or false.', 400)
    return jsonify(svc.decide_adjustment(adjustment_id, d['approve'], g.user['email'], key()))


@bp.post('/batches/<batch_id>/dispose')
@require_role('superadmin')
def dispose(batch_id):
    if (blocked := enabled()) is not None:
        return blocked
    d = data()
    return jsonify(svc.dispose(batch_id, d.get('qty'), g.user['email'], key(), d.get('reason')))


@bp.get('/movements')
@require_role()
def movements():
    if (blocked := enabled()) is not None:
        return blocked
    try:
        limit = min(100, max(1, int(request.args.get('limit', 25))))
    except ValueError:
        return jsonify({'error': 'Invalid limit.'}), 400
    query = {'product_id': request.args['product_id']} if request.args.get('product_id') else {}
    return jsonify([svc.clean(m) for m in db.stock_movements.find(query).sort('at', -1).limit(limit)])


@bp.get('/summary')
@require_role()
def summary():
    if (blocked := enabled()) is not None:
        return blocked
    from datetime import date
    today = date.today().isoformat()
    rows = list(db.inventory_batches.aggregate([
        {'$group': {'_id': '$product_id', 'on_hand': {'$sum': '$on_hand'},
                    'reserved': {'$sum': '$reserved'}}},
        {'$sort': {'_id': 1}}, {'$limit': 500}
    ]))
    result = []
    for row in rows:
        # Available must consider batch condition and expiration.
        eligible = db.inventory_batches.find({'product_id': row['_id'],
            'condition': 'available', 'unverified': False, 'expires_on': {'$gte': today}})
        available = sum(b['on_hand'] - b['reserved'] for b in eligible)
        result.append({'product_id': row['_id'], 'on_hand': row['on_hand'],
            'reserved': row['reserved'], 'available': available})
    return jsonify(result)


@bp.post('/returns')
@require_role('superadmin', 'subadmin')
def receive_return():
    if (blocked := enabled()) is not None:
        return blocked
    d = data()
    return jsonify(svc.receive_return(d.get('order_id'), d.get('product_id'), d.get('lot'),
        d.get('expires_on'), d.get('qty'), g.user['email'], key(), d.get('reason'))), 201


@bp.post('/batches/<batch_id>/restrict')
@require_role('superadmin')
def restrict_batch(batch_id):
    if (blocked := enabled()) is not None:
        return blocked
    d = data()
    return jsonify(svc.restrict_batch(batch_id, d.get('condition'),
        g.user['email'], key(), d.get('reason')))
