import json

from fastapi import HTTPException

from ..core.db import transaction
from ..models import ReportRequest
from ..repositories import quiz_repository
from .report_service import generate_report


async def settle(pool, user_id, req):
    async with transaction(pool) as conn:
        quiz = await quiz_repository.lock_quiz(conn, user_id, req.quiz_id)
        if quiz is None:
            raise HTTPException(404, '闯关记录不存在')
        existing = await quiz_repository.saved_report(conn, user_id, req.quiz_id)
        if existing is not None:
            return existing
        questions = json.loads(quiz['questions_json'])
        question_ids = {q['id'] for q in questions}
        by_id = {record.question_id: record for record in req.answer_records}
        if not questions or len(by_id) != len(req.answer_records) or set(by_id) != question_ids:
            raise HTTPException(422, '请完成本轮全部题目，不得重复或添加题目')
        records = []
        for question in questions:
            record = by_id[question['id']]
            selected = record.selected_answers
            if (not selected or len(set(selected)) != len(selected)
                    or not set(selected).issubset(option['key'] for option in question['options'])
                    or (question['type'] != 'multiple' and len(selected) != 1)):
                raise HTTPException(422, '作答选项不合法')
            records.append({**record.model_dump(), 'is_correct': sorted(selected) == sorted(question['answer'])})
        trusted_request = ReportRequest(quiz_id=req.quiz_id, topic=quiz['title'], questions=questions,
                                       answer_records=records)
        report = generate_report(trusted_request)
        await quiz_repository.save_result(conn, user_id, req.quiz_id, records, report)
        return report


async def detail(pool, user_id, quiz_id):
    result = await quiz_repository.detail(pool, user_id, quiz_id)
    if result is None:
        raise HTTPException(404, '闯关记录不存在或尚未完成')
    return result
