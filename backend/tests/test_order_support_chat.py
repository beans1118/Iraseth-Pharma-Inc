"""Order support tests: customer email authorization and staff inbox isolation."""
from uuid import uuid4
import pytest
from modules.support import routes as support
from config import Config


@pytest.fixture
def support_order(test_db, monkeypatch):
    assert test_db.name == 'iraseth_test'
    oid = 'CHAT-' + uuid4().hex
    # Keep IP-based rate-limit buckets isolated across tests and repeated runs.
    request_key = uuid4().hex[:24]
    monkeypatch.setattr(support, 'request_context_key', lambda: request_key)
    test_db.orders.insert_one({'id': oid, 'email': 'buyer@example.invalid', 'client': 'Sample buyer', 'facility': 'Example facility', 'status': 'Pending'})
    yield oid
    test_db.support_challenges.delete_many({'order_id': oid})
    test_db.support_sessions.delete_many({'order_id': oid})
    test_db.support_messages.delete_many({'order_id': oid})
    test_db.support_threads.delete_many({'order_id': oid})
    test_db.orders.delete_one({'id': oid})
    test_db.support_rate_limits.delete_many({'_id': {'$regex': '^(request-ip|verify-ip):' + request_key + ':'}})
    for candidate_email in ('buyer@example.invalid', 'other@example.invalid'):
        key = support.fingerprint(oid.casefold() + ':' + candidate_email)[:24]
        test_db.support_rate_limits.delete_many({'_id': {'$regex': '^request-order:' + key + ':'}})
    key = support.fingerprint(oid)[:24]
    test_db.support_rate_limits.delete_many({'_id': {'$regex': '^chat-customer:' + key + ':'}})


def test_unknown_order_does_not_disclose_existence(client, support_order, monkeypatch):
    monkeypatch.setattr(Config, 'SMTP_HOST', 'fake-smtp')
    sent = []
    monkeypatch.setattr(support, 'send_email', lambda *args: sent.append(args) or True)
    known = client.post('/api/v2/support/request-code', json={'order_number': support_order, 'email': 'buyer@example.invalid'})
    unknown = client.post('/api/v2/support/request-code', json={'order_number': support_order, 'email': 'other@example.invalid'})
    assert known.status_code == unknown.status_code == 200
    assert known.get_json() == unknown.get_json()
    assert len(sent) == 1


def test_customer_cannot_read_without_email_code(client, support_order):
    r = client.get('/api/v2/support/customer/messages')
    assert r.status_code == 401
    r = client.get('/api/v2/support/customer/messages', headers={'X-Support-Token': 'bad-token'})
    assert r.status_code == 401


def test_verified_customer_chat_and_staff_reply(client, auth, support_order, monkeypatch):
    monkeypatch.setattr(Config, 'SMTP_HOST', 'fake-smtp')
    sent=[]
    monkeypatch.setattr(support, 'send_email', lambda *args: sent.append(args) or True)
    request = client.post('/api/v2/support/request-code', json={'order_number': support_order, 'email': 'buyer@example.invalid'})
    assert request.status_code == 200
    import re
    code=re.search(r'\b\d{6}\b', sent[0][2]).group(0)
    verified=client.post('/api/v2/support/verify-code', json={'order_number': support_order,'email':'buyer@example.invalid','code':code})
    assert verified.status_code == 200, verified.get_json()
    key=verified.get_json()['support_token']
    ch={'X-Support-Token':key}
    assert client.post('/api/v2/support/customer/messages',headers=ch,json={'body':'Can you check my delivery?'}).status_code==201
    assert client.get('/api/v2/support/customer/messages',headers=ch).get_json()[0]['body']=='Can you check my delivery?'
    staff=auth('superadmin')
    inbox=client.get('/api/v2/support/staff/threads',headers=staff)
    assert inbox.status_code==200
    assert any(t['order_id']==support_order for t in inbox.get_json())
    assert client.post('/api/v2/support/staff/threads/'+support_order+'/messages',headers=staff,json={'body':'We are checking.'}).status_code==201
    assert len(client.get('/api/v2/support/customer/messages',headers=ch).get_json())==2
    assert client.post('/api/v2/support/verify-code',json={'order_number':support_order,'email':'buyer@example.invalid','code':code}).status_code==401


def test_no_smtp_does_not_issue_fake_code(client, support_order, monkeypatch):
    monkeypatch.setattr(Config, 'SMTP_HOST', '')
    res=client.post('/api/v2/support/request-code',json={'order_number':support_order,'email':'buyer@example.invalid'})
    assert res.status_code==503


def test_order_number_is_case_insensitive_but_session_uses_canonical_id(client, support_order, monkeypatch):
    monkeypatch.setattr(Config, 'SMTP_HOST', 'fake-smtp')
    sent = []
    monkeypatch.setattr(support, 'send_email', lambda *args: sent.append(args) or True)
    response = client.post('/api/v2/support/request-code', json={
        'order_number': support_order.upper(), 'email': 'BUYER@example.invalid'})
    assert response.status_code == 200, response.get_json()
    assert len(sent) == 1
    import re
    code = re.search(r'\b\d{6}\b', sent[0][2]).group(0)
    verified = client.post('/api/v2/support/verify-code', json={
        'order_number': support_order.lower(), 'email': 'buyer@example.invalid', 'code': code})
    assert verified.status_code == 200, verified.get_json()
    assert verified.get_json()['order_number'] == support_order


def test_no_smtp_response_does_not_reveal_order_existence(client, support_order, monkeypatch):
    monkeypatch.setattr(Config, 'SMTP_HOST', '')
    known = client.post('/api/v2/support/request-code', json={
        'order_number': support_order, 'email': 'buyer@example.invalid'})
    unknown = client.post('/api/v2/support/request-code', json={
        'order_number': support_order, 'email': 'other@example.invalid'})
    assert known.status_code == unknown.status_code == 503
    assert known.get_json() == unknown.get_json()
