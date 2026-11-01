"""Order support: email OTP for customers, staff JWT for private inbox.

No customer account is required. Order ID alone is not an authenticator.
Requires configured SMTP in order to issue customer access codes.
"""
import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, g, jsonify, request
from pymongo import ReturnDocument

from config import Config
from extensions import db
from utils.email import send_email
from utils.security import require_role

bp = Blueprint('order_support', __name__, url_prefix='/api/v2/support')
log = logging.getLogger(__name__)
MAX_MESSAGE = 2000
MAX_HISTORY = 100
CODE_TTL = timedelta(minutes=10)
SESSION_TTL = timedelta(hours=12)


def utcnow():
    return datetime.now(timezone.utc)


def fingerprint(value):
    return hmac.new(Config.JWT_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


def valid_text(value, length):
    return isinstance(value, str) and 0 < len(value.strip()) <= length


def serialize(message):
    return {k: v for k, v in message.items() if k != '_id'}


def customer_session(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        supplied = request.headers.get('X-Support-Token', '')
        if not supplied or len(supplied) > 180:
            return jsonify(error='Support session required.'), 401
        session = db.support_sessions.find_one({'token_hash': fingerprint(supplied), 'expires_at': {'$gt': utcnow()}})
        if not session:
            return jsonify(error='Support session expired. Request a new email code.'), 401
        g.support_session = session
        return fn(*args, **kwargs)
    return wrapped


def throttle(key, limit, window_seconds):
    """Conservative fixed window, atomic counters, no client-controlled proxy headers."""
    bucket = int(utcnow().timestamp()) // window_seconds
    record = db.support_rate_limits.find_one_and_update(
        {'_id': f'{key}:{bucket}'},
        {'$inc': {'count': 1}, '$setOnInsert': {'expires_at': utcnow() + timedelta(seconds=window_seconds * 2)}},
        upsert=True, return_document=ReturnDocument.AFTER,
    )
    return record['count'] > limit


def request_context_key():
    # Remote address is safe only with configured trusted proxy middleware.
    return fingerprint(request.remote_addr or 'unknown')[:24]


@bp.post('/request-code')
def request_code():
    data = request.get_json(silent=True) or {}
    order_id = str(data.get('order_number') or '').strip()
    email = str(data.get('email') or '').strip().lower()
    if not (valid_text(order_id, 64) and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email)):
        return jsonify(error='Enter a valid order number and email.'), 400
    if not Config.SMTP_HOST:
        # Avoid disclosing whether an order exists when email delivery is unavailable.
        return jsonify(error='Email verification is temporarily unavailable. Contact Iraseth support.'), 503
    if throttle('request-ip:' + request_context_key(), 10, 3600):
        return jsonify(error='Too many attempts. Try again later.'), 429
    if throttle('request-order:' + fingerprint(order_id.casefold() + ':' + email)[:24], 3, 900):
        return jsonify(error='Too many requests. Try again in 15 minutes.'), 429
    # Same response whether or not the order is found (no order enumeration).
    response = {'message': 'If the order and email match, a verification code will be sent.'}
    order = db.orders.find_one({
        'id': {'$regex': '^' + re.escape(order_id) + '$', '$options': 'i'},
        'email': {'$regex': '^' + re.escape(email) + '$', '$options': 'i'},
    }, {'id': 1, 'email': 1})
    if not order:
        return jsonify(response), 200
    # Use the canonical ID stored on the order for messages and sessions.
    order_id = order['id']
    code = f'{secrets.randbelow(1_000_000):06d}'
    challenge_id = secrets.token_urlsafe(24)
    db.support_challenges.insert_one({
        'id': challenge_id, 'order_id': order_id, 'email': email,
        'code_hash': fingerprint(challenge_id + ':' + code), 'attempts': 0,
        'expires_at': utcnow() + CODE_TTL,
    })
    delivered = send_email(email, f'Iraseth order {order_id} support code',
                           f'Your Iraseth order support verification code is {code}.\nIt expires in 10 minutes.\nIf you did not request this, ignore this email.')
    if not delivered:
        db.support_challenges.delete_one({'id': challenge_id})
        return jsonify(error='Unable to send verification email. Please try again later.'), 503
    return jsonify(response), 200


@bp.post('/verify-code')
def verify_code():
    data = request.get_json(silent=True) or {}
    order_id = str(data.get('order_number') or '').strip()
    email = str(data.get('email') or '').strip().lower()
    code = str(data.get('code') or '').strip()
    if not re.fullmatch(r'\d{6}', code) or not valid_text(order_id, 64):
        return jsonify(error='Invalid or expired code.'), 400
    if throttle('verify-ip:' + request_context_key(), 25, 900):
        return jsonify(error='Too many attempts. Try again later.'), 429
    challenge = db.support_challenges.find_one({
        'order_id': {'$regex': '^' + re.escape(order_id) + '$', '$options': 'i'},
        'email': email, 'expires_at': {'$gt': utcnow()}}, sort=[('_id', -1)])
    if not challenge:
        return jsonify(error='Invalid or expired code.'), 401
    # Atomically claim an attempt; prevents unlimited parallel brute forcing.
    claimed = db.support_challenges.find_one_and_update(
        {'_id': challenge['_id'], 'attempts': {'$lt': 5}, 'expires_at': {'$gt': utcnow()}},
        {'$inc': {'attempts': 1}}, return_document=ReturnDocument.AFTER)
    if not claimed or not hmac.compare_digest(claimed['code_hash'], fingerprint(claimed['id'] + ':' + code)):
        return jsonify(error='Invalid or expired code.'), 401
    canonical_order_id = challenge['order_id']
    db.support_challenges.delete_many({'order_id': canonical_order_id, 'email': email})
    session_token = secrets.token_urlsafe(36)
    db.support_sessions.insert_one({'token_hash': fingerprint(session_token), 'order_id': canonical_order_id, 'email': email,
                                    'expires_at': utcnow() + SESSION_TTL})
    return jsonify({'support_token': session_token, 'order_number': canonical_order_id, 'expires_in_seconds': 43200}), 200


@bp.get('/customer/messages')
@customer_session
def customer_messages():
    oid = g.support_session['order_id']
    items = list(db.support_messages.find({'order_id': oid}, {'_id': 0}).sort('at', -1).limit(MAX_HISTORY))
    return jsonify(list(reversed(items)))


@bp.post('/customer/messages')
@customer_session
def post_customer_message():
    data = request.get_json(silent=True) or {}
    body = data.get('body')
    if not valid_text(body, MAX_MESSAGE):
        return jsonify(error='Message must be between 1 and 2000 characters.'), 400
    oid = g.support_session['order_id']
    if throttle('chat-customer:' + fingerprint(oid)[:24], 30, 60):
        return jsonify(error='Too many messages. Try again shortly.'), 429
    message = {'id': secrets.token_hex(16), 'order_id': oid, 'sender': 'customer', 'body': body.strip(), 'at': utcnow().isoformat()}
    db.support_messages.insert_one(message)
    db.support_threads.update_one({'order_id': oid}, {'$set': {'updated_at': message['at'], 'last_message': body.strip()[:160]},
                       '$setOnInsert': {'created_at': message['at'], 'status': 'open'}}, upsert=True)
    return jsonify(serialize(message)), 201


@bp.get('/staff/threads')
@require_role()
def staff_threads():
    threads = list(db.support_threads.find({}, {'_id': 0}).sort('updated_at', -1).limit(100))
    # Authorized staff can see order metadata in the inbox; do not expose private email in customer APIs.
    orders = {o['id']: o for o in db.orders.find({'id': {'$in': [t['order_id'] for t in threads]}},
                                                   {'_id': 0, 'id': 1, 'client': 1, 'facility': 1, 'status': 1})}
    return jsonify([{**t, 'order': orders.get(t['order_id'])} for t in threads])


@bp.get('/staff/threads/<order_id>/messages')
@require_role()
def staff_messages(order_id):
    if not db.support_threads.find_one({'order_id': order_id}):
        return jsonify(error='Conversation not found.'), 404
    messages = list(db.support_messages.find({'order_id': order_id}, {'_id': 0}).sort('at', -1).limit(MAX_HISTORY))
    return jsonify(list(reversed(messages)))


@bp.post('/staff/threads/<order_id>/messages')
@require_role()
def staff_reply(order_id):
    if not db.support_threads.find_one({'order_id': order_id}):
        return jsonify(error='Conversation not found.'), 404
    body = (request.get_json(silent=True) or {}).get('body')
    if not valid_text(body, MAX_MESSAGE):
        return jsonify(error='Message must be between 1 and 2000 characters.'), 400
    message = {'id': secrets.token_hex(16), 'order_id': order_id, 'sender': 'staff',
               'sender_email': g.user['email'], 'body': body.strip(), 'at': utcnow().isoformat()}
    db.support_messages.insert_one(message)
    db.support_threads.update_one({'order_id': order_id}, {'$set': {'updated_at': message['at'], 'last_message': body.strip()[:160]}})
    return jsonify(serialize(message)), 201

@bp.post('/staff/threads')
@require_role()
def staff_create_message():
    """Start a staff message attached to an existing order.

    This does not email the customer or grant access. Customers still use
    their order email and a valid OTP to access the order conversation.
    """
    data = request.get_json(silent=True) or {}
    supplied_id = str(data.get('order_id') or '').strip()
    body = data.get('body')
    if not valid_text(supplied_id, 64) or not valid_text(body, MAX_MESSAGE):
        return jsonify(error='Select an existing order and enter a message (1–2000 characters).'), 400
    order = db.orders.find_one({'id': {'$regex': '^' + re.escape(supplied_id) + '$', '$options': 'i'}}, {'id': 1, 'email': 1})
    if not order or not order.get('email'):
        return jsonify(error='An order with a registered customer email is required.'), 404
    order_id = order['id']
    now = utcnow().isoformat()
    message = {'id': secrets.token_hex(16), 'order_id': order_id, 'sender': 'staff',
               'sender_email': g.user['email'], 'body': body.strip(), 'at': now}
    db.support_threads.update_one({'order_id': order_id},
                                  {'$set': {'updated_at': now, 'last_message': body.strip()[:160]},
                                   '$setOnInsert': {'order_id': order_id, 'status': 'open'}},
                                  upsert=True)
    db.support_messages.insert_one(message)
    return jsonify(serialize(message)), 201
