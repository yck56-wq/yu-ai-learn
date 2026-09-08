"""仅验证真实模型出题服务；完整 HTTP 流程需通过微信登录后在小程序验证。"""
import json
from app.models import QuizRequest
from app.services.quiz_service import generate_quiz, QuizGenerationError

if __name__ == '__main__':
    request = QuizRequest(**{
        'user_input': '学习 RAG 与传统搜索的区别、向量检索、企业知识库维护、回答引用和幻觉边界。请结合实际工作案例。',
        'question_count': 5, 'difficulty': 'mixed',
    })
    try:
        quiz = generate_quiz(request)
    except QuizGenerationError as exc:
        print(json.dumps({'status': exc.status_code, 'message': str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from None
    print(json.dumps({'status':200,'count':len(quiz['questions']),
        'unique_stems':len({q['stem'] for q in quiz['questions']}),
        'questions':[{'stem':q['stem'],'knowledge_point':q['knowledge_point'],'type':q['type']} for q in quiz['questions']]}, ensure_ascii=False, indent=2))
