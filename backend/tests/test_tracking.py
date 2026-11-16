"""Only fixture-owned records in the conftest-locked iraseth_test database."""
import re
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from datetime import timedelta
import pytest

from modules.tracking import routes as tracking
from routes.orders import VALID_STATUSES
from modules.inventory.service import ORDER_STATUSES
from modules.quotations.routes import ALLOWED_STATUS, OPEN_STATUS


@pytest.fixture
def tracked(client, test_db):
    client.environ_base['REMOTE_ADDR'] = 'tracking-' + uuid4().hex
    ref = 'RFQ-' + uuid4().hex[:12].upper()
    oid = 'PYTEST-' + uuid4().hex
    email = uuid4().hex + '@example.invalid'
    inquiry = {'id': ref, 'status': 'New', 'email': email, 'fullName': 'Private Name',
               'phone': 'private phone', 'company': 'private organization', 'notes': 'private note',
               'items': [{'id': 'private-id', 'price': 123}], 'idempotency_key': uuid4().hex,
               'payload_hash': 'private hash', 'created_at': '2026-01-01T00:00:00+00:00'}
    test_db.quotations.insert_one(inquiry)
    try:
        yield ref, oid, email
    finally:
        test_db.tracking_challenges.delete_many({'reference': ref})
        test_db.communication_requests.delete_many({'reference': ref})
        test_db.quotation_events.delete_many({'reference': ref})
        test_db.quotations.delete_one({'id': ref})
        test_db.orders.delete_one({'id': oid})
        test_db.support_threads.delete_many({'order_id': oid})
        test_db.support_messages.delete_many({'order_id': oid})


@pytest.mark.parametrize('state,label', [('New','Inquiry Received'), ('In Review','Under Review'),
    ('Declined','Inquiry Declined'), ('Responded','Response Recorded'), ('Closed','Inquiry Closed')])
def test_inquiry_states(client, test_db, tracked, state, label):
    ref, _, _ = tracked
    test_db.quotations.update_one({'id': ref}, {'$set': {'status': state}})
    response = client.post('/api/public/tracking', json={'reference': ref.lower()})
    assert response.status_code == 200
    assert response.get_json()['status'] == label
    assert set(response.get_json()) == {'reference', 'status', 'milestones'}
    assert response.headers['Cache-Control'] == 'no-store'
    for step in response.get_json()['milestones']:
        assert set(step) == {'status', 'at'}
    assert all(word not in response.get_data(as_text=True) for word in ['Private Name', 'private phone', 'private-id', 'private hash', 'private note', '123'])


@pytest.mark.parametrize('state,label', [('Pending','Pending Order'), ('Approved','Approved / Processing'),
    ('Processing','Approved / Processing'), ('Fulfilled','Fulfilled / Completed'), ('Cancelled','Cancelled')])
def test_official_states(client, test_db, tracked, state, label):
    ref, oid, _ = tracked
    test_db.quotations.update_one({'id': ref}, {'$set': {'status': 'Accepted', 'order_id': oid}})
    test_db.orders.insert_one({'id': oid, 'source_inquiry_id': ref, 'status': state,
        'client': 'PRIVATE', 'lines': [{'secret': 1}], 'total': 999, 'notes': ['private'],
        'approved_at': '2026-01-02T00:00:00+00:00' if state in ('Approved', 'Fulfilled') else None,
        'fulfilled_at': '2026-01-03T00:00:00+00:00' if state == 'Fulfilled' else None})
    result = client.post('/api/public/tracking', json={'reference': ref})
    assert result.status_code == 200
    assert result.get_json()['status'] == label
    assert oid not in result.get_data(as_text=True)
    assert 'PRIVATE' not in result.get_data(as_text=True)
    assert result.get_json()['milestones'][-1]['status'] == label
    assert test_db.orders.count_documents({'source_inquiry_id': ref}) == 1


def test_mapping_covers_all_domain_values():
    assert set(VALID_STATUSES) | set(ORDER_STATUSES) == {'Pending', 'Approved', 'Processing', 'Fulfilled', 'Cancelled'}
    assert set(ALLOWED_STATUS) | set(OPEN_STATUS) == {'New', 'In Review', 'Accepted', 'Declined', 'Responded', 'Closed'}


def test_missing_or_invalid_links_never_guess_progress(client, test_db, tracked):
    ref, oid, _ = tracked
    test_db.quotations.update_one({'id': ref}, {'$set': {'status': 'Accepted', 'order_id': oid}})
    assert client.post('/api/public/tracking', json={'reference': ref}).status_code == 503
    # A manually entered employee order must not be attached by guessing its ID.
    test_db.orders.insert_one({'id': oid, 'status': 'Fulfilled'})
    assert client.post('/api/public/tracking', json={'reference': ref}).status_code == 503


@pytest.mark.parametrize('value', [None, {}, 'PO-20260001', 'RFQ-123', 'RFQ-AAAAAAAAAAAA<script>', {'$ne': None}])
def test_invalid_references(client, tracked, value):
    assert client.post('/api/public/tracking', json={'reference': value}).status_code == 400


def test_unknown_and_rate_limits(client, tracked):
    ref = 'RFQ-' + uuid4().hex[:12].upper()
    assert client.post('/api/public/tracking', json={'reference': ref}).status_code == 404
    for _ in range(29):
        client.post('/api/public/tracking', json={'reference': ref})
    response = client.post('/api/public/tracking', json={'reference': ref})
    assert response.status_code == 429
    assert int(response.headers['Retry-After']) > 0


def request_and_code(client, monkeypatch, ref, email, action='email_update', **fields):
    delivered = []
    monkeypatch.setattr(tracking.Config, 'SMTP_HOST', 'smtp.test.invalid')
    monkeypatch.setattr(tracking, 'send_email', lambda *args: delivered.append(args) or True)
    response = client.post('/api/public/tracking/request-code', json={'reference': ref, 'email': email, 'action': action, **fields})
    assert response.status_code == 200, response.get_json()
    assert 'Private' not in delivered[0][2] and ref not in delivered[0][2]
    return response.get_json()['challenge'], re.search(r'\b\d{6}\b', delivered[0][2]).group()


@pytest.mark.parametrize('alternate', [False, True])
def test_verified_requests_and_ownership(client, test_db, tracked, monkeypatch, alternate):
    ref, oid, email = tracked
    test_db.quotations.update_one({'id': ref}, {'$set': {'status': 'Accepted', 'order_id': oid}})
    test_db.orders.insert_one({'id': oid, 'source_inquiry_id': ref, 'status': 'Pending', 'email': email})
    used = 'alternate-' + email if alternate else email
    challenge, code = request_and_code(client, monkeypatch, ref, used, 'contact', message='Where is my order?')
    assert test_db.communication_requests.count_documents({'reference': ref}) == 0
    assert client.post('/api/public/tracking/verify-code', json={'challenge': challenge, 'code': 'bad'}).status_code == 400
    response = client.post('/api/public/tracking/verify-code', json={'challenge': challenge, 'code': code})
    assert response.status_code == 201
    assert set(response.get_json()) == {'message'}
    row = test_db.communication_requests.find_one({'reference': ref})
    assert row['status'] == ('needs_review' if alternate else 'queued')
    assert test_db.quotations.find_one({'id': ref})['email'] == email
    assert test_db.support_messages.count_documents({'order_id': oid}) == (0 if alternate else 1)
    assert client.post('/api/public/tracking/verify-code', json={'challenge': challenge, 'code': code}).status_code == 401
    assert test_db.communication_requests.count_documents({'reference': ref}) == 1


def test_delivery_failure_and_unconfigured_provider(client, test_db, tracked, monkeypatch):
    ref, _, email = tracked
    monkeypatch.setattr(tracking.Config, 'SMTP_HOST', '')
    data = {'reference': ref, 'email': email, 'action': 'email_update'}
    assert client.post('/api/public/tracking/request-code', json=data).status_code == 503
    monkeypatch.setattr(tracking.Config, 'SMTP_HOST', 'smtp.test.invalid')
    monkeypatch.setattr(tracking, 'send_email', lambda *args: False)
    assert client.post('/api/public/tracking/request-code', json=data).status_code == 503
    assert test_db.tracking_challenges.count_documents({'reference': ref}) == 0
    assert test_db.communication_requests.count_documents({'reference': ref}) == 0


def test_code_attempt_limit_and_expiry(client, test_db, tracked, monkeypatch):
    ref, _, email = tracked
    challenge, code = request_and_code(client, monkeypatch, ref, email)
    wrong = '000000' if code != '000000' else '111111'
    for _ in range(5):
        assert client.post('/api/public/tracking/verify-code', json={'challenge': challenge, 'code': wrong}).status_code == 401
    assert client.post('/api/public/tracking/verify-code', json={'challenge': challenge, 'code': code}).status_code == 401
    assert not test_db.communication_requests.find_one({'reference': ref})


def test_workflow_staff_rbac_and_delivery(client, auth, test_db, tracked, monkeypatch):
    ref, _, email = tracked
    challenge, code = request_and_code(client, monkeypatch, ref, email)
    client.post('/api/public/tracking/verify-code', json={'challenge': challenge, 'code': code})
    row = test_db.communication_requests.find_one({'reference': ref})
    url = f"/api/v2/communication-requests/{row['id']}/send-update"
    assert client.get('/api/v2/communication-requests').status_code == 401
    assert client.post(url).status_code == 401
    assert client.get('/api/v2/communication-requests', headers=auth('admin')).status_code == 200
    assert client.post(url, headers=auth('admin')).status_code == 403
    headers = auth('subadmin')
    monkeypatch.setattr(tracking, 'send_email', lambda *args: False)
    assert client.post(url, headers=headers).status_code == 503
    assert test_db.communication_requests.find_one({'id': row['id']})['status'] == 'queued'
    sent = []
    monkeypatch.setattr(tracking, 'send_email', lambda *args: sent.append(args) or True)
    assert client.post(url, headers=headers).get_json()['status'] == 'sent'
    assert client.post(url, headers=headers).get_json()['status'] == 'sent'
    assert len(sent) == 1


def test_alternate_email_cannot_get_update(client, auth, test_db, tracked, monkeypatch):
    ref, _, email = tracked
    challenge, code = request_and_code(client, monkeypatch, ref, 'different-' + email)
    client.post('/api/public/tracking/verify-code', json={'challenge': challenge, 'code': code})
    row = test_db.communication_requests.find_one({'reference': ref})
    sent = []
    monkeypatch.setattr(tracking, 'send_email', lambda *args: sent.append(args) or True)
    assert client.post(f"/api/v2/communication-requests/{row['id']}/send-update", headers=auth()).status_code == 409
    assert not sent


def test_expired_challenge_cannot_queue_request(client, test_db, tracked, monkeypatch):
    ref, _, email = tracked
    challenge, code = request_and_code(client, monkeypatch, ref, email)
    test_db.tracking_challenges.update_one({'id':challenge}, {'$set':{'expires_at':tracking.utcnow()-timedelta(seconds=1)}})
    assert client.post('/api/public/tracking/verify-code', json={'challenge':challenge,'code':code}).status_code == 401
    assert not test_db.communication_requests.find_one({'reference':ref})


def test_close_does_not_claim_success_for_in_flight_send(client, auth, test_db, tracked, monkeypatch):
    ref, _, email = tracked
    challenge, code = request_and_code(client, monkeypatch, ref, email)
    client.post('/api/public/tracking/verify-code', json={'challenge':challenge,'code':code})
    row = test_db.communication_requests.find_one({'reference':ref})
    test_db.communication_requests.update_one({'id':row['id']}, {'$set':{'status':'sending'}})
    result = client.post(f"/api/v2/communication-requests/{row['id']}/close", headers=auth('subadmin'))
    assert result.status_code == 409
    assert test_db.communication_requests.find_one({'id':row['id']})['status'] == 'sending'
