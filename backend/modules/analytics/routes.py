"""Read-only operational metrics. No stock or invoice writes."""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, jsonify, request
from extensions import db
from utils.security import require_role

bp = Blueprint('analytics_api', __name__, url_prefix='/api/v2/analytics')


def recent_days():
    try:
        days = int(request.args.get('days', '30'))
    except ValueError:
        return None
    return days if days in (7, 30, 90) else None


def count_by(collection, field):
    return {str(row['_id'] if row['_id'] is not None else 'Unknown'): row['count'] for row in
            collection.aggregate([{'$group': {'_id': '$'+field, 'count': {'$sum': 1}}}])}


@bp.get('/overview')
@require_role('superadmin', 'admin', 'subadmin')
def overview():
    days = recent_days()
    if days is None:
        return jsonify({'error': 'days must be 7, 30, or 90.'}), 400
    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=days - 1)).isoformat()
    expiry_end = (today + timedelta(days=90)).isoformat()
    # Current batch snapshot, not inferred from old catalog-level quantity.
    grouped = list(db.inventory_batches.aggregate([{'$group': {
        '_id': None, 'on_hand': {'$sum': '$on_hand'}, 'reserved': {'$sum': '$reserved'},
        'batch_count': {'$sum': 1}}}]))
    stock = grouped[0] if grouped else {}
    eligible = list(db.inventory_batches.aggregate([
        {'$match': {'condition': 'available', 'unverified': {'$ne': True},
                    'expires_on': {'$gte': today.isoformat()}, 'on_hand': {'$gt': 0}}},
        {'$group': {'_id': None, 'available': {'$sum': {'$subtract': ['$on_hand', '$reserved']}}}}
    ]))
    expiry_count = db.inventory_batches.count_documents({
        'on_hand': {'$gt': 0}, 'expires_on': {'$gte': today.isoformat(), '$lte': expiry_end}})
    # Movement timestamps are UTC ISO strings in the existing engine.
    movements = list(db.stock_movements.aggregate([
        {'$match': {'at': {'$gte': cutoff}}},
        {'$group': {'_id': {'day': {'$substrBytes': ['$at', 0, 10]}, 'action': '$action'},
                    'events': {'$sum': 1}, 'units': {'$sum': '$qty'}}},
        {'$sort': {'_id.day': 1, '_id.action': 1}}]))
    return jsonify({
        'period_days': days, 'as_of_utc': datetime.now(timezone.utc).isoformat(),
        'products': db.products.count_documents({}),
        'batch_count': stock.get('batch_count', 0),
        'on_hand': stock.get('on_hand', 0),
        'reserved': stock.get('reserved', 0),
        'available_eligible': max(0, (eligible[0].get('available', 0) if eligible else 0)),
        'expiring_batches_90d': expiry_count,
        'orders_by_status': count_by(db.orders, 'status'),
        'invoices_by_status': count_by(db.invoices, 'status'),
        'movement_trends': [{'day': r['_id']['day'], 'action': r['_id']['action'] or 'other',
                            'events': r['events'], 'units': r['units']} for r in movements],
        'scope_note': 'Snapshot counts cover the database. Movement trends cover the selected UTC date window. Invoice events do not represent payments.'
    })
