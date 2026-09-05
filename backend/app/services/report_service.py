from ..models import ReportRequest

def generate_report(req: ReportRequest):
    by_id={q.id:q for q in req.questions}; correct=0; mastered=[]; weak=[]
    for r in req.answer_records:
        q=by_id.get(r.question_id); ok=bool(q and sorted(r.selected_answers)==sorted(q.answer))
        if ok: correct+=1; mastered.append(q.knowledge_point)
        elif q: weak.append(q.knowledge_point)
    total=len(req.answer_records); accuracy=round(correct/total*100) if total else 0
    return {'accuracy':accuracy,'mastered_points':list(dict.fromkeys(mastered)),'weak_points':list(dict.fromkeys(weak)),'three_line_summary':[f'本轮完成{total}题，答对{correct}题。','掌握点：'+('、'.join(dict.fromkeys(mastered)) or '暂无'),'薄弱点：'+('、'.join(dict.fromkeys(weak)) or '暂无')],'advice':['优先复习薄弱知识点并重新练习。'] if weak else ['继续用题目检验理解。'],'share_quote':'把知识做成关卡，记忆会更深。'}
