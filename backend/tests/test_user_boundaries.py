import asyncio

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

TEST_KEY = 'test-only-signing-key-with-at-least-32-bytes'


@pytest.mark.parametrize('expiration', [None, [], {}, 'not-a-date'])
def test_malformed_expiration_is_401_not_server_error(client, expiration):
    token = jwt.encode({'user_id': 1, 'exp': expiration}, TEST_KEY, algorithm='HS256')
    response = client.get('/api/v1/user/profile', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 401


@pytest.mark.parametrize('status,data', [(500, {}), (200, []), (200, {}), (200, {'openid': 'x', 'errcode': 40013})])
def test_wechat_bad_responses_do_not_create_users(client, monkeypatch, db, status, data):
    async def get(self, url, **kwargs):
        return httpx.Response(status, json=data)
    monkeypatch.setattr(httpx.AsyncClient, 'get', get)
    response = client.post('/api/v1/user/login', json={'code': 'test'})
    assert response.status_code == 502
    with db.cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n FROM users')
        assert cur.fetchone()['n'] == 0


def test_missing_wechat_config_fails_without_external_request(client, monkeypatch):
    monkeypatch.setattr(settings, 'wechat_app_secret', '')
    assert client.post('/api/v1/user/login', json={'code': 'test'}).status_code == 503


def test_missing_signing_key_prevents_startup(monkeypatch):
    monkeypatch.setattr(settings, 'jwt_secret', '')
    with pytest.raises(RuntimeError, match='signing key'):
        with TestClient(app):
            pass


def test_database_start_failure_is_redacted(monkeypatch):
    import aiomysql
    async def fail(**kwargs):
        raise OSError('private-connection-detail')
    monkeypatch.setattr(aiomysql, 'create_pool', fail)
    with pytest.raises(RuntimeError, match='Database connection failed') as exc:
        with TestClient(app):
            pass
    assert 'private-connection-detail' not in str(exc.value)


@pytest.mark.parametrize('fields', [{'nickname': '\n学习\t者'}, {'nickname': None}, {'avatar_url': None}, {'avatar_url': 'https://avatar.local/a.png'}])
def test_profile_rejects_control_characters_and_null(client, login, fields):
    headers, _ = login()
    assert client.put('/api/v1/user/profile', headers=headers, json=fields).status_code == 422


def test_avatar_can_be_reset(client, login):
    headers, _ = login()
    assert client.put('/api/v1/user/profile', headers=headers, json={'avatar_url': ''}).status_code == 200


def test_all_business_routes_require_authentication(client):
    for path in ('/api/v1/user/profile', '/api/v1/user/quizzes', '/api/v1/user/quizzes/unknown'):
        assert client.get(path).status_code == 401
    assert client.put('/api/v1/user/profile', json={'nickname': 'test'}).status_code == 401
    assert client.post('/api/v1/report/generate', json={'quiz_id': 'q', 'topic': 'x', 'questions': [], 'answer_records': []}).status_code == 401


def test_cancellation_rolls_back_transaction(client, db):
    from app.core.db import transaction
    async def cancelled_write():
        async with transaction(app.state.pool) as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO users(openid,nickname,avatar_url) VALUES('cancelled-test','test','')")
            raise asyncio.CancelledError()
    with pytest.raises(BaseException):
        client.portal.call(cancelled_write)
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM users WHERE openid='cancelled-test'")
        assert cur.fetchone()['n'] == 0
