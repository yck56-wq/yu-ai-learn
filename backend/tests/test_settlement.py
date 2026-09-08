import copy
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import quiz_service
from test_quiz_generation import quiz_data


@pytest.fixture
def generated(client, login, monkeypatch):
    headers, user = login()
    sequence = []
    def generate(count=5):
        data = quiz_data(count)
        data['quiz_id'] = 'test-quiz-' + str(len(sequence))
        sequence.append(data)
        monkeypatch.setattr(quiz_service, 'generate_quiz', lambda req: data)
        response = client.post('/api/v1/quiz/generate', headers=headers,
                               json={'user_input': '学习 RAG', 'question_count': count})
        assert response.status_code == 200
        return response.json()['data']
    return headers, user, generate


def payload(quiz, correct=4):
    return {'quiz_id': quiz['quiz_id'], 'topic': quiz['title'], 'questions': quiz['questions'],
            'answer_records': [{'question_id': q['id'], 'selected_answers': q['answer'] if i < correct else ['B'],
                                'duration_ms': 1000, 'is_correct': True} for i, q in enumerate(quiz['questions'])]}


def test_generated_quiz_is_persisted_but_not_in_history(client, generated, db):
    headers, user, generate = generated
    quiz = generate()
    with db.cursor() as cur:
        cur.execute('SELECT * FROM quiz_sessions WHERE quiz_id=%s', (quiz['quiz_id'],))
        stored = cur.fetchone()
        assert stored is not None
        assert stored['user_id'] == user['id']
        assert json.loads(stored['questions_json']) == quiz['questions']
        assert stored['user_input'] == '学习 RAG'
    history = client.get('/api/v1/user/quizzes', headers=headers)
    assert history.status_code == 200
    assert history.json()['data']['total'] == 0
    assert client.get('/api/v1/user/quizzes/' + quiz['quiz_id'], headers=headers).status_code == 404


def test_settlement_uses_database_answers_and_awards_exact_xp(client, generated, db):
    headers, user, generate = generated
    quiz = generate()
    body = copy.deepcopy(payload(quiz))
    body['questions'][-1]['answer'] = ['B']
    body['topic'] = 'forged topic'
    response = client.post('/api/v1/report/generate', headers=headers, json=body)
    assert response.status_code == 200
    assert response.json()['data']['accuracy'] == 80
    profile = client.get('/api/v1/user/profile', headers=headers).json()['data']
    assert profile['total_xp'] == 80
    assert profile['correct_count'] == 4
    assert profile['quiz_count'] == 1
    assert profile['average_accuracy'] == 80
    detail = client.get('/api/v1/user/quizzes/' + quiz['quiz_id'], headers=headers).json()['data']
    assert detail['questions'][-1]['answer'] == ['A']
    assert detail['answer_records'][-1]['is_correct'] is False
    assert detail['report'] == response.json()['data']


def test_repeated_or_concurrent_settlement_is_idempotent(client, generated, db):
    headers, user, generate = generated
    quiz = generate()
    body = payload(quiz)
    with ThreadPoolExecutor(max_workers=5) as workers:
        responses = list(workers.map(lambda _: client.post('/api/v1/report/generate', headers=headers, json=body), range(5)))
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json() == responses[0].json() for r in responses)
    different = payload(quiz, correct=0)
    assert client.post('/api/v1/report/generate', headers=headers, json=different).json() == responses[0].json()
    assert client.get('/api/v1/user/profile', headers=headers).json()['data']['total_xp'] == 80
    with db.cursor() as cur:
        for table in ('reports', 'answer_records'):
            cur.execute('SELECT COUNT(*) AS n FROM ' + table)
            assert cur.fetchone()['n'] == 1


def test_two_different_rounds_can_settle_concurrently_without_deadlock(client, generated, monkeypatch):
    import aiomysql
    headers, _, generate = generated
    rounds = [generate(), generate()]
    original = aiomysql.Cursor.execute
    arrived = 0
    gate = asyncio.Event()
    async def synchronized_update(cursor, query, args=None):
        nonlocal arrived
        if query.startswith('UPDATE users SET total_xp='):
            arrived += 1
            if arrived == 2:
                gate.set()
            await asyncio.wait_for(gate.wait(), timeout=5)
        return await original(cursor, query, args)
    monkeypatch.setattr(aiomysql.Cursor, 'execute', synchronized_update)
    with ThreadPoolExecutor(max_workers=2) as workers:
        responses = list(workers.map(lambda quiz: client.post('/api/v1/report/generate', headers=headers, json=payload(quiz)), rounds))
    assert [response.status_code for response in responses] == [200, 200]
    assert client.get('/api/v1/user/profile', headers=headers).json()['data']['total_xp'] == 160
    assert client.get('/api/v1/user/quizzes', headers=headers).json()['data']['total'] == 2


@pytest.mark.parametrize('defect', ['missing', 'duplicate', 'extra', 'empty', 'invalid_option', 'duplicate_option', 'too_many_single', 'negative_duration'])
def test_invalid_round_cannot_be_settled(client, generated, defect):
    headers, _, generate = generated
    body = payload(generate())
    records = body['answer_records']
    if defect == 'missing': records.pop()
    if defect == 'duplicate': records[-1] = records[0]
    if defect == 'extra': records.append({**records[0], 'question_id': 'extra'})
    if defect == 'empty': records[0]['selected_answers'] = []
    if defect == 'invalid_option': records[0]['selected_answers'] = ['Z']
    if defect == 'duplicate_option': records[0]['selected_answers'] = ['A', 'A']
    if defect == 'too_many_single': records[0]['selected_answers'] = ['A', 'B']
    if defect == 'negative_duration': records[0]['duration_ms'] = -1
    assert client.post('/api/v1/report/generate', headers=headers, json=body).status_code == 422
    assert client.get('/api/v1/user/profile', headers=headers).json()['data']['total_xp'] == 0
    assert client.get('/api/v1/user/quizzes', headers=headers).json()['data']['total'] == 0


def test_other_user_cannot_submit_or_read_quiz(client, generated, login):
    headers, _, generate = generated
    quiz = generate()
    bob, _ = login('bob')
    assert client.post('/api/v1/report/generate', headers=bob, json=payload(quiz)).status_code == 404
    assert client.post('/api/v1/report/generate', headers=headers, json=payload(quiz)).status_code == 200
    assert client.get('/api/v1/user/quizzes/' + quiz['quiz_id'], headers=bob).status_code == 404
    assert client.get('/api/v1/user/quizzes', headers=bob).json()['data']['items'] == []
    assert client.get('/api/v1/user/quizzes/not-found', headers=headers).status_code == 404


def test_history_pagination_and_weighted_accuracy(client, generated):
    headers, _, generate = generated
    first, second = generate(3), generate(5)
    client.post('/api/v1/report/generate', headers=headers, json=payload(first, correct=3))
    client.post('/api/v1/report/generate', headers=headers, json=payload(second, correct=1))
    profile = client.get('/api/v1/user/profile', headers=headers).json()['data']
    assert profile['average_accuracy'] == 50
    assert profile['total_xp'] == 80
    assert profile['quiz_count'] == 2
    page1 = client.get('/api/v1/user/quizzes?page=1&page_size=1', headers=headers).json()['data']
    page2 = client.get('/api/v1/user/quizzes?page=2&page_size=1', headers=headers).json()['data']
    assert page1['total'] == 2 and page1['page_size'] == 1 and page1['page'] == 1
    assert page1['items'][0]['quiz_id'] == second['quiz_id']
    assert page2['items'][0]['quiz_id'] == first['quiz_id']
    assert page1['items'][0]['question_count'] == 5
    assert page1['items'][0]['accuracy'] == 20


@pytest.mark.parametrize('query', ['page=0', 'page_size=0', 'page_size=51'])
def test_history_pagination_bounds(client, login, query):
    headers, _ = login()
    assert client.get('/api/v1/user/quizzes?' + query, headers=headers).status_code == 422


def test_report_insert_failure_rolls_back_answers_and_xp(client, generated, db):
    headers, user, generate = generated
    quiz = generate()
    with db.cursor() as cur:
        cur.execute("CREATE TRIGGER fail_report BEFORE INSERT ON reports FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='test-injected-failure'")
    try:
        response = client.post('/api/v1/report/generate', headers=headers, json=payload(quiz))
        assert response.status_code == 503
        assert 'test-injected-failure' not in response.text
        with db.cursor() as cur:
            cur.execute('SELECT COUNT(*) AS n FROM answer_records')
            assert cur.fetchone()['n'] == 0
            cur.execute('SELECT total_xp FROM users WHERE id=%s', (user['id'],))
            assert cur.fetchone()['total_xp'] == 0
    finally:
        with db.cursor() as cur:
            cur.execute('DROP TRIGGER fail_report')
    assert client.post('/api/v1/report/generate', headers=headers, json=payload(quiz)).status_code == 200


def test_failed_generation_leaves_no_session(client, login, monkeypatch, db):
    headers, _ = login()
    def fail(_):
        raise quiz_service.QuizGenerationError('test generation failure')
    monkeypatch.setattr(quiz_service, 'generate_quiz', fail)
    assert client.post('/api/v1/quiz/generate', headers=headers, json={'user_input': 'RAG'}).status_code == 502
    with db.cursor() as cur:
        cur.execute('SELECT COUNT(*) AS n FROM quiz_sessions')
        assert cur.fetchone()['n'] == 0


def test_lifespan_restart_preserves_completed_history(db, wechat, monkeypatch):
    monkeypatch.setattr(quiz_service, 'generate_quiz', lambda _: quiz_data())
    with TestClient(app) as first:
        token = first.post('/api/v1/user/login', json={'code': 'alice'}).json()['data']['token']
        headers = {'Authorization': 'Bearer ' + token}
        quiz = first.post('/api/v1/quiz/generate', headers=headers, json={'user_input': 'RAG'}).json()['data']
        assert first.post('/api/v1/report/generate', headers=headers, json=payload(quiz)).status_code == 200
        pool = app.state.pool
    assert pool.closed
    with TestClient(app) as restarted:
        assert restarted.get('/api/v1/user/quizzes', headers=headers).json()['data']['total'] == 1
        assert restarted.get('/api/v1/user/quizzes/' + quiz['quiz_id'], headers=headers).json()['data']['report']['accuracy'] == 80
