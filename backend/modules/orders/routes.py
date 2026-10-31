"""Order reservation lifecycle for batch-mode operations."""
from flask import Blueprint, g, jsonify, request
from config import Config
from utils.security import require_role
from modules.inventory import service as svc

bp = Blueprint('batch_orders', __name__, url_prefix='/api/v2/orders')

@bp.errorhandler(svc.InventoryProblem)
def error(exc):
    return jsonify({'error': str(exc)}), exc.status

def enabled():
    if not Config.BATCH_MODE:
        return jsonify({'error': 'Batch mode disabled. Complete migration first.'}), 503

@bp.post('/<order_id>/approve')
@require_role('superadmin', 'subadmin')
def approve(order_id):
    if (blocked := enabled()) is not None:
        return blocked
    return jsonify(svc.reserve_order(order_id, g.user['email'], request.headers.get('Idempotency-Key')))

@bp.post('/<order_id>/fulfill')
@require_role('superadmin', 'subadmin')
def fulfill(order_id):
    if (blocked := enabled()) is not None:
        return blocked
    return jsonify(svc.fulfill_reserved(order_id, g.user['email'], request.headers.get('Idempotency-Key')))

@bp.post('/<order_id>/cancel')
@require_role('superadmin', 'subadmin')
def cancel(order_id):
    if (blocked := enabled()) is not None:
        return blocked
    return jsonify(svc.cancel_order(order_id, g.user['email'], request.headers.get('Idempotency-Key')))
