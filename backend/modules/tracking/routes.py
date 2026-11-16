"""Reference-only results never contain customer, line, pricing, staff or order IDs.

Email ownership is proved separately. A different verified email is routed to
staff review and never becomes the inquiry owner or receives private details.
"""
import hmac
import re
import secrets
from datetime import timedelta

from flask import Blueprint, g, jsonify, request
from pymongo import ReturnDocument

from config import Config
from extensions import db
from modules.quotations.routes import ALLOWED_STATUS, OPEN_STATUS
from routes.orders import VALID_STATUSES
from modules.inventory.service import ORDER_STATUSES
from modules.support.routes import fingerprint, utcnow, throttle, request_context_key, CODE_TTL
from utils.email import send_email
from utils.security import require_role, client_rate_limit

bp = Blueprint('tracking', __name__, url_prefix='/api/public/tracking')
staff_bp = Blueprint('tracking_requests', __name__, url_prefix='/api/v2/communication-requests')
REF = re.compile(r'RFQ-[A-F0-9]{12}')


def reference(value):
    if not isinstance(value, str) or not REF.fullmatch(value.strip().upper()):
        raise ValueError('Enter an RFQ reference such as RFQ-012345ABCDEF.')
    return value.strip().upper()


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('A JSON object is required.')
    return data


@bp.before_request
def protect():
    if request.method == 'OPTIONS':
        return None
    if request.content_length and request.content_length > 8000:
        return jsonify(error='Request too large.'), 413
    blocked = client_rate_limit('rfq-tracking', 30)
    if blocked is not None:
        return blocked
    return client_rate_limit('rfq-tracking-hour', 300, 3600)


@bp.after_request
@staff_bp.after_request
def private_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@bp.errorhandler(ValueError)
def invalid(exc):
    return jsonify(error=str(exc)), 400


def public_state(inquiry, order):
    """Translate only statuses supported by the actual inquiry/order workflows."""
    current = inquiry.get('status')
    inquiry_labels = {'New': 'Inquiry Received', 'In Review': 'Under Review',
                      'Declined': 'Inquiry Declined', 'Responded': 'Response Recorded', 'Closed': 'Inquiry Closed'}
    if current != 'Accepted':
        if current not in set(ALLOWED_STATUS) | set(OPEN_STATUS):
            raise ValueError('Status awaiting staff review.')
        return inquiry_labels.get(current, 'Status awaiting staff review.')
    if not order:
        raise ValueError('Linked order status is temporarily unavailable. Please contact our team.')
    status = order.get('status')
    if status not in set(VALID_STATUSES) | set(ORDER_STATUSES):
        raise ValueError('Order status awaiting staff review.')
    return {'Pending': 'Pending Order', 'Approved': 'Approved / Processing',
            'Processing': 'Approved / Processing', 'Fulfilled': 'Fulfilled / Completed',
            'Cancelled': 'Cancelled'}[status]


def linked_order(inquiry):
    if inquiry.get('status') != 'Accepted':
        return None
    # The atomic acceptance flow owns this unique link. Never create an order here.
    order = db.orders.find_one({'source_inquiry_id': inquiry['id']},
        {'id': 1, 'status': 1, 'approved_at': 1, 'fulfilled_at': 1, 'cancelled_at': 1})
    if order and inquiry.get('order_id') == order['id']:
        return order
    return None


def result(inquiry):
    order = linked_order(inquiry)
    status = public_state(inquiry, order)
    milestones = [{'status': 'Inquiry Received', 'at': inquiry.get('created_at')}]
    # Observed events only: no simulated/future progress steps or private notes.
    for event in db.quotation_events.find({'reference': inquiry['id']}, {'to': 1, 'at': 1}).sort('at', 1):
        label = {'In Review': 'Under Review', 'Accepted': 'Pending Order', 'Declined': 'Inquiry Declined'}.get(event.get('to'))
        if label:
            milestones.append({'status': label, 'at': event.get('at')})
    if order:
        for key, label in [('approved_at', 'Approved / Processing'), ('fulfilled_at', 'Fulfilled / Completed'), ('cancelled_at', 'Cancelled')]:
            if order.get(key):
                milestones.append({'status': label, 'at': order[key]})
    if milestones[-1]['status'] != status:
        milestones.append({'status': status, 'at': None})
    return {'reference': inquiry['id'], 'status': status, 'milestones': milestones}


@bp.post('')
def track():
    data = body()
    ref = reference(data.get('reference'))
    inquiry = db.quotations.find_one({'id': ref}, {'id': 1, 'status': 1, 'created_at': 1, 'order_id': 1})
    if not inquiry:
        return jsonify(error='Reference unavailable. Check the code or contact our team.'), 404
    try:
        return jsonify(result(inquiry))
    except ValueError as exc:
        return jsonify(error=str(exc)), 503


@bp.post('/request-code')
def request_code():
    data = body()
    ref = reference(data.get('reference'))
    email = data.get('email')
    action = data.get('action')
    message = data.get('message', '')
    if not isinstance(email, str) or len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email.strip()):
        raise ValueError('Enter a valid email address.')
    if action not in ('email_update', 'contact') or not isinstance(message, str) or len(message) > 2000:
        raise ValueError('Invalid communication request.')
    if action == 'contact' and not message.strip():
        raise ValueError('Enter a message for our team.')
    email = email.strip().lower()
    if throttle('rfq-code-ip:' + request_context_key(), 10, 3600) or throttle('rfq-code-email:' + fingerprint(email), 3, 900):
        return jsonify(error='Too many verification attempts. Try again later.'), 429
    if not Config.SMTP_HOST:
        return jsonify(error='Email verification is unavailable. No email was sent. Please contact our team directly.'), 503
    # The same challenge flow for known/unknown RFQs avoids disclosing ownership
    # or reference existence through email requests. Email contains no order data.
    code = f'{secrets.randbelow(1_000_000):06d}'
    challenge = secrets.token_urlsafe(24)
    doc = {'id': challenge, 'reference': ref, 'email': email, 'action': action,
           'message': message.strip(), 'code_hash': fingerprint(challenge + ':' + code),
           'attempts': 0, 'expires_at': utcnow() + CODE_TTL, 'ready': False}
    db.tracking_challenges.insert_one(doc)
    if not send_email(email, 'Iraseth communication verification',
                      f'Your verification code is {code}. It expires in 10 minutes.\nThis verifies your email only; it does not establish ownership of an inquiry.\nIgnore this email if you did not request it.'):
        db.tracking_challenges.delete_one({'id': challenge})
        return jsonify(error='Unable to send verification email. No request has been submitted.'), 503
    db.tracking_challenges.update_one({'id': challenge}, {'$set': {'ready': True}})
    return jsonify(challenge=challenge, message='Verification email accepted by the email provider. Enter the code to submit your request.')


@bp.post('/verify-code')
def verify_code():
    data = body()
    challenge_id, code = data.get('challenge'), data.get('code')
    if not isinstance(challenge_id, str) or len(challenge_id) > 100 or not isinstance(code, str) or not re.fullmatch(r'\d{6}', code):
        raise ValueError('Invalid or expired code.')
    if throttle('rfq-verify:' + request_context_key(), 25, 900):
        return jsonify(error='Too many verification attempts.'), 429
    challenge = db.tracking_challenges.find_one_and_update(
        {'id': challenge_id, 'attempts': {'$lt': 5}, 'ready': True, 'expires_at': {'$gt': utcnow()}},
        {'$inc': {'attempts': 1}}, return_document=ReturnDocument.AFTER)
    if not challenge or not hmac.compare_digest(challenge['code_hash'], fingerprint(challenge_id + ':' + code)):
        return jsonify(error='Invalid or expired code.'), 401
    # One transaction consumes the challenge and queues exactly one request.
    def queue(session):
        existing = db.communication_requests.find_one({'challenge_id': challenge_id}, session=session)
        if existing:
            return True
        consumed = db.tracking_challenges.find_one_and_delete({'id': challenge_id, 'ready': True, 'expires_at': {'$gt': utcnow()}}, session=session)
        if not consumed:
            return False
        inquiry = db.quotations.find_one({'id': challenge['reference']}, session=session)
        if not inquiry:
            return False
        same = str(inquiry.get('email', '')).strip().lower() == challenge['email']
        now = utcnow().isoformat()
        workflow = {'id': secrets.token_hex(16), 'challenge_id': challenge_id,
                    'reference': inquiry['id'], 'email': challenge['email'],
                    'action': challenge['action'], 'message': challenge['message'],
                    'ownership': 'original_email' if same else 'staff_review',
                    'status': 'queued' if same else 'needs_review', 'created_at': now}
        # Reuse the verified order-linked inbox only for the original customer.
        if same and inquiry.get('order_id'):
            order = db.orders.find_one({'id': inquiry['order_id'], 'source_inquiry_id': inquiry['id']}, session=session)
            if order:
                oid = order['id']
                text = challenge['message'] if challenge['action'] == 'contact' else 'Customer requested an email status update.'
                db.support_messages.insert_one({'id': workflow['id'], 'order_id': oid, 'sender': 'customer', 'body': text, 'at': now}, session=session)
                db.support_threads.update_one({'order_id': oid}, {'$set': {'updated_at': now, 'last_message': text[:160]},
                    '$setOnInsert': {'created_at': now, 'status': 'open'}}, upsert=True, session=session)
        db.communication_requests.insert_one(workflow, session=session)
        return True
    with db.client.start_session() as session:
        queued = session.with_transaction(queue)
    if not queued:
        return jsonify(error='Request unavailable. Check the reference or contact our team directly.'), 404
    return jsonify(message='Your verified request is queued for staff review. Email ownership alone does not establish inquiry ownership. No status update email has been sent.'), 201


@staff_bp.get('')
@require_role()
def requests():
    return jsonify(list(db.communication_requests.find({}, {'_id': 0, 'challenge_id': 0}).sort('created_at', -1).limit(200)))


@staff_bp.post('/<request_id>/<action>')
@require_role('superadmin', 'subadmin')
def resolve(request_id, action):
    if action not in ('close', 'send-update'):
        return jsonify(error='Invalid action.'), 400
    row = db.communication_requests.find_one({'id': request_id})
    if not row:
        return jsonify(error='Request not found.'), 404
    if row['status'] in ('sent', 'closed'):
        return jsonify(status=row['status'])
    now = utcnow().isoformat()
    if action == 'close':
        closed = db.communication_requests.find_one_and_update({'id': request_id, 'status': {'$in': ['queued', 'needs_review']}},
            {'$set': {'status': 'closed', 'resolved_by': g.user['email'], 'resolved_at': now}}, return_document=ReturnDocument.AFTER)
        if not closed:
            return jsonify(error='Request is already being handled. Refresh its status.'), 409
        return jsonify(status='closed')
    inquiry = db.quotations.find_one({'id': row['reference']})
    if not inquiry or row['ownership'] != 'original_email' or str(inquiry.get('email', '')).strip().lower() != row['email']:
        return jsonify(error='This address requires staff ownership review. Private updates are disabled.'), 409
    if not Config.SMTP_HOST:
        return jsonify(error='Email provider is not configured. No update was sent.'), 503
    try:
        status = result(inquiry)['status']
    except ValueError as exc:
        return jsonify(error=str(exc)), 409
    # Claim a send so simultaneous staff clicks cannot send duplicate messages.
    claimed = db.communication_requests.update_one({'id': request_id, 'status': 'queued'}, {'$set': {'status': 'sending'}})
    if not claimed.modified_count:
        return jsonify(error='Request is already being handled. Refresh its status.'), 409
    if not send_email(row['email'], f"Iraseth inquiry {row['reference']} update", f"Reference: {row['reference']}\nCurrent status: {status}\nContact our team for further assistance."):
        db.communication_requests.update_one({'id': request_id, 'status': 'sending'}, {'$set': {'status': 'queued', 'delivery_error_at': now}})
        return jsonify(error='Email delivery failed. Request remains queued.'), 503
    db.communication_requests.update_one({'id': request_id, 'status': 'sending'},
        {'$set': {'status': 'sent', 'resolved_by': g.user['email'], 'resolved_at': now}})
    return jsonify(status='sent')
