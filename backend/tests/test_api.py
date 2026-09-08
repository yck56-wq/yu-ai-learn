def test_health(client):
    r=client.get('/api/v1/health')
    assert r.status_code==200
    assert r.json()['code']==0

def test_quiz_generate_returns_structured_quiz(monkeypatch, client, login):
    from app.services import quiz_service
    monkeypatch.setattr(quiz_service, 'generate_quiz', lambda req: {'quiz_id':'q1','title':'RAG','summary':'s','questions':[]})
    headers, _ = login()
    r=client.post('/api/v1/quiz/generate',headers=headers,json={'user_input':'学习 RAG','question_count':3,'difficulty':'mixed'})
    assert r.status_code==200 and r.json()['data']['quiz_id']=='q1'

def test_report_accuracy_is_computed(client, login, monkeypatch):
    payload={'quiz_id':'q1','topic':'RAG','questions':[{'id':'q1','type':'single','stem':'x','options':[{'key':'A','text':'a'}],'answer':['A'],'explanation':'e','knowledge_point':'概念','difficulty':'easy'}],'answer_records':[{'question_id':'q1','selected_answers':['A'],'duration_ms':100}]}
    from app.services import quiz_service
    headers, _ = login()
    monkeypatch.setattr(quiz_service, 'generate_quiz', lambda req: {'quiz_id': 'q1', 'title': 'RAG', 'summary': 's', 'questions': payload['questions']})
    assert client.post('/api/v1/quiz/generate', headers=headers, json={'user_input': 'RAG'}).status_code == 200
    r=client.post('/api/v1/report/generate',headers=headers,json=payload)
    assert r.status_code==200 and r.json()['data']['accuracy']==100
