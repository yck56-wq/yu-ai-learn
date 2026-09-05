"""手动运行的真实 DeepSeek 冒烟验证，不纳入 pytest；不输出配置或异常原文。"""
import json
from fastapi.testclient import TestClient
from app.main import app

if __name__ == '__main__':
    response = TestClient(app).post('/api/v1/quiz/generate', json={
        'user_input': '学习 RAG 与传统搜索的区别、向量检索、企业知识库维护、回答引用和幻觉边界。请结合实际工作案例。',
        'question_count': 5, 'difficulty': 'mixed',
    })
    body = response.json()
    if response.status_code != 200:
        print(json.dumps({'status':response.status_code,'message':body.get('message','生成失败')}, ensure_ascii=False))
        raise SystemExit(1)
    quiz = body['data']
    print(json.dumps({'status':200,'count':len(quiz['questions']),
        'unique_stems':len({q['stem'] for q in quiz['questions']}),
        'questions':[{'stem':q['stem'],'knowledge_point':q['knowledge_point'],'type':q['type']} for q in quiz['questions']]}, ensure_ascii=False, indent=2))
