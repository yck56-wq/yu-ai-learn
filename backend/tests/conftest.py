import os
from pathlib import Path

import httpx
import pymysql
import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient

ENV = dotenv_values(Path(__file__).resolve().parents[1] / '.env')
os.environ['MYSQL_DATABASE'] = 'yu_ai_learn_test'
os.environ['JWT_SECRET'] = 'test-only-signing-key-with-at-least-32-bytes'

from app.main import app


@pytest.fixture
def db():
    conn = pymysql.connect(host=ENV['MYSQL_HOST'], port=int(ENV['MYSQL_PORT']),
                           user=ENV['MYSQL_USER'], password=ENV['MYSQL_PASSWORD'],
                           database='yu_ai_learn_test', charset='utf8mb4', autocommit=True,
                           cursorclass=pymysql.cursors.DictCursor)
    with conn.cursor() as cur:
        cur.execute('SELECT DATABASE() AS db')
        assert cur.fetchone()['db'] == 'yu_ai_learn_test'
        for table in ('reports', 'answer_records', 'quiz_sessions', 'knowledge_documents', 'users'):
            cur.execute('DELETE FROM ' + table)
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def wechat(monkeypatch):
    calls = []
    async def get(self, url, *, params):
        assert url == 'https://api.weixin.qq.com/sns/jscode2session'
        assert params['grant_type'] == 'authorization_code'
        code = params['js_code']
        calls.append(code)
        if code == 'timeout':
            raise httpx.TimeoutException('sensitive-upstream-detail')
        if code == 'used':
            return httpx.Response(200, json={'errcode': 40163, 'errmsg': 'sensitive-upstream-detail'})
        if code == 'busy':
            return httpx.Response(200, json={'errcode': -1})
        if code == 'malformed':
            return httpx.Response(200, text='not JSON')
        return httpx.Response(200, json={'openid': 'test-openid-' + code, 'session_key': 'test-session-placeholder'})
    monkeypatch.setattr(httpx.AsyncClient, 'get', get)
    return calls


@pytest.fixture
def login(client, wechat):
    def do_login(code='alice'):
        response = client.post('/api/v1/user/login', json={'code': code})
        assert response.status_code == 200
        result = response.json()['data']
        return {'Authorization': 'Bearer ' + result['token']}, result['user']
    return do_login
