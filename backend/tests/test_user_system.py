from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import jwt
import pytest

TEST_KEY = 'test-only-signing-key-with-at-least-32-bytes'


def test_login_creates_user_and_reuses_identity(client, wechat, db):
    first = client.post('/api/v1/user/login', json={'code': 'alice'})
    assert first.status_code == 200
    body = first.json()['data']
    assert body['user']['nickname'] == '学习者'
    assert body['user']['total_xp'] == 0
    assert 'openid' not in body['user'] and 'session_key' not in first.text
    claims = jwt.decode(body['token'], TEST_KEY, algorithms=['HS256'])
    assert claims['user_id'] == body['user']['id']
    assert 6 * 86400 < claims['exp'] - datetime.now(timezone.utc).timestamp() <= 7 * 86400
    second = client.post('/api/v1/user/login', json={'code': 'alice'})
    assert second.json()['data']['user']['id'] == body['user']['id']
    with db.cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n FROM users')
        assert cur.fetchone()['n'] == 1


def test_concurrent_login_creates_only_one_account(client, wechat, db):
    with ThreadPoolExecutor(max_workers=4) as workers:
        responses = list(workers.map(lambda _: client.post('/api/v1/user/login', json={'code': 'alice'}), range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert len({r.json()['data']['user']['id'] for r in responses}) == 1


@pytest.mark.parametrize('code,status', [('used', 401), ('busy', 503), ('timeout', 502), ('malformed', 502)])
def test_login_failure_is_safe(client, wechat, code, status):
    response = client.post('/api/v1/user/login', json={'code': code})
    assert response.status_code == status
    assert response.json()['data'] is None
    assert 'sensitive-upstream-detail' not in response.text


@pytest.mark.parametrize('code', ['', ' ', 'x' * 513])
def test_login_rejects_empty_and_oversized_code(client, code):
    assert client.post('/api/v1/user/login', json={'code': code}).status_code == 422


@pytest.mark.parametrize('authorization', ['', 'Basic invalid', 'Bearer invalid'])
def test_unauthenticated_generation_does_not_call_model(client, monkeypatch, authorization):
    from app.services import quiz_service
    calls = []
    def forbidden(req):
        calls.append(req)
        return {'quiz_id': 'should-not-generate'}
    monkeypatch.setattr(quiz_service, 'generate_quiz', forbidden)
    response = client.post('/api/v1/quiz/generate', headers={'Authorization': authorization}, json={'user_input': 'RAG'})
    assert response.status_code == 401
    assert calls == []
    assert response.json()['data'] is None


@pytest.mark.parametrize('claims,key,algorithm', [
    ({'user_id': 1, 'exp': 1}, TEST_KEY, 'HS256'),
    ({'user_id': 1}, TEST_KEY, 'HS256'),
    ({'exp': 9999999999}, TEST_KEY, 'HS256'),
    ({'user_id': True, 'exp': 9999999999}, TEST_KEY, 'HS256'),
    ({'user_id': '1', 'exp': 9999999999}, TEST_KEY, 'HS256'),
    ({'user_id': 1, 'exp': 9999999999}, 'wrong-test-signing-key-with-32-bytes', 'HS256'),
    ({'user_id': 1, 'exp': 9999999999}, TEST_KEY * 2, 'HS384'),
])
def test_invalid_jwt_rejected(client, claims, key, algorithm):
    token = jwt.encode(claims, key, algorithm=algorithm)
    assert client.get('/api/v1/user/profile', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_deleted_user_token_rejected(client, login, db):
    headers, user = login()
    with db.cursor() as cur:
        cur.execute('DELETE FROM users WHERE id=%s', (user['id'],))
    assert client.get('/api/v1/user/profile', headers=headers).status_code == 401


def test_profile_is_private_and_updates_only_allowed_fields(client, login):
    headers, alice = login()
    bob_headers, _ = login('bob')
    initial = client.get('/api/v1/user/profile', headers=headers).json()['data']
    assert initial == {**alice, 'quiz_count': 0, 'correct_count': 0, 'average_accuracy': 0}
    response = client.put('/api/v1/user/profile', headers=headers, json={'nickname': '  新昵称  '})
    assert response.status_code == 200
    assert response.json()['data']['nickname'] == '新昵称'
    assert client.get('/api/v1/user/profile', headers=bob_headers).json()['data']['nickname'] == '学习者'
    assert client.put('/api/v1/user/profile', headers=headers, json={'total_xp': 999}).status_code == 422


@pytest.mark.parametrize('payload', [
    {'nickname': ''}, {'nickname': ' '}, {'nickname': '字' * 101},
    {'avatar_url': 'wxfile://temp/a.png'}, {'avatar_url': 'http://tmp/a.png'},
    {'avatar_url': 'https://localhost/a.png'}, {'avatar_url': 'https://127.0.0.1/a.png'},
    {'avatar_url': 'javascript:alert(1)'}, {},
])
def test_profile_rejects_invalid_data(client, login, payload):
    headers, _ = login()
    assert client.put('/api/v1/user/profile', headers=headers, json=payload).status_code == 422


def test_profile_accepts_public_https_avatar(client, login):
    headers, _ = login()
    response = client.put('/api/v1/user/profile', headers=headers, json={'avatar_url': 'https://example.com/avatar.png'})
    assert response.status_code == 200
    assert response.json()['data']['avatar_url'] == 'https://example.com/avatar.png'
