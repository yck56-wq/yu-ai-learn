import copy
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_openai import ChatOpenAI
from app.main import app
from app.services import quiz_service


def quiz_data(count=5):
    stems = [
        'RAG 如何把检索结果用于生成回答？',
        '为什么企业知识库需要定期更新文档版本？',
        '向量检索找不到相关内容时应采取什么措施？',
        '使用检索增强是否意味着模型绝不会产生幻觉？',
        '如何评估一份回答的引用是否支持其结论？',
    ]
    points = ['检索与生成流程', '知识库维护', '检索相关性', '幻觉边界', '引用验证']
    return {'quiz_id': 'provider-id', 'title': 'RAG 入门', 'summary': 'RAG 基础与应用', 'questions': [
        {'id': f'q{i+1}', 'type': 'single', 'stem': stems[i],
         'options': [{'key':'A','text':f'{points[i]}的有效处理'}, {'key':'B','text':'忽略资料来源'}, {'key':'C','text':'跳过必要验证'}, {'key':'D','text':'仅凭直觉判断'}],
         'answer': ['A'], 'explanation': f'需要结合{points[i]}验证实际结果。',
         'knowledge_point': points[i], 'difficulty': 'easy'} for i in range(count)]}


@pytest.fixture
def provider(monkeypatch):
    clients = []
    def install(responses):
        requests = []
        def handle(request):
            payload = json.loads(request.content)
            requests.append(payload)
            index = min(len(requests)-1, len(responses)-1)
            response = responses[index]
            if isinstance(response, int):
                return httpx.Response(response, json={'error':{'message':'provider unavailable','type':'api_error'}})
            content = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
            return httpx.Response(200, json={'id':'chat-test','object':'chat.completion','created':1,'model':'deepseek-chat',
                'choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':10,'completion_tokens':10,'total_tokens':20}})
        client = httpx.Client(transport=httpx.MockTransport(handle))
        clients.append(client)
        model = ChatOpenAI(model='deepseek-chat', base_url='https://api.deepseek.com', api_key='test-only-placeholder', http_client=client, max_retries=0)
        monkeypatch.setattr(quiz_service, 'get_llm', lambda: model)
        return requests
    yield install
    for client in clients:
        client.close()


def generate(count=5):
    return TestClient(app).post('/api/v1/quiz/generate', json={'user_input':'学习 RAG','question_count':count,'difficulty':'mixed'})


def test_uses_json_object_and_returns_unique_topics(provider):
    requests = provider([quiz_data()])
    response = generate()
    assert response.status_code == 200
    body = response.json()['data']
    assert len({q['stem'] for q in body['questions']}) == 5
    assert len({q['knowledge_point'] for q in body['questions']}) == 5
    assert requests[0].get('response_format') == {'type':'json_object'}
    assert body['quiz_id'] != 'provider-id'


@pytest.mark.parametrize('variant', ['exact', 'punctuation', 'near'])
def test_rejects_duplicate_stems_and_regenerates(provider, variant):
    bad = quiz_data()
    stem = bad['questions'][0]['stem']
    bad['questions'][1]['stem'] = {'exact': stem, 'punctuation': 'RAG 如何把检索结果用于生成回答!!!', 'near':'RAG 如何把检索结果用于生成答案？'}[variant]
    requests = provider([bad, quiz_data()])
    response = generate()
    assert response.status_code == 200
    assert response.json()['data']['questions'][1]['stem'] == '为什么企业知识库需要定期更新文档版本？'
    assert len(requests) == 2


@pytest.mark.parametrize('defect', ['count', 'answer', 'empty_explanation', 'same_point', 'same_options'])
def test_retries_invalid_quiz_instead_of_returning_it(provider, defect):
    bad = quiz_data()
    if defect == 'count': bad['questions'].pop()
    if defect == 'answer': bad['questions'][0]['answer'] = ['Z']
    if defect == 'empty_explanation': bad['questions'][0]['explanation'] = ' '
    if defect == 'same_point':
        for q in bad['questions']: q['knowledge_point'] = '核心概念'
    if defect == 'same_options':
        bad['questions'][1]['options'] = copy.deepcopy(bad['questions'][0]['options'])
    requests = provider([bad, quiz_data()])
    response = generate()
    assert response.status_code == 200
    assert response.json()['data']['questions'] == quiz_data()['questions']
    assert len(requests) == 2


def test_repeated_bad_output_fails_explicitly_without_local_template(provider):
    bad = quiz_data()
    bad['questions'] = [copy.deepcopy(bad['questions'][0]) for _ in range(5)]
    requests = provider([bad])
    response = generate()
    assert response.status_code == 502
    assert response.json()['data'] is None
    assert response.json()['code'] != 0
    assert len(requests) == 2


def test_empty_or_malformed_json_is_retried(provider):
    requests = provider(['not JSON', quiz_data(3)])
    response = generate(3)
    assert response.status_code == 200
    assert len(response.json()['data']['questions']) == 3
    assert len(requests) == 2


def test_missing_model_returns_configuration_error(monkeypatch):
    monkeypatch.setattr(quiz_service, 'get_llm', lambda: None)
    response = generate()
    assert response.status_code == 503
    assert response.json()['data'] is None


def test_auth_failure_never_fakes_a_success(provider):
    requests = provider([401])
    response = generate()
    assert response.status_code == 502
    assert response.json()['data'] is None
    assert len(requests) == 1


def test_transient_provider_failure_retries_and_returns_valid_quiz(provider):
    requests = provider([500, quiz_data()])
    response = generate()
    assert response.status_code == 200
    assert response.json()['data']['questions'] == quiz_data()['questions']
    assert len(requests) == 2
