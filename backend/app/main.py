from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .models import QuizRequest, ReportRequest
from .services import quiz_service, report_service
app=FastAPI(title='开卷有戏 API')
@app.exception_handler(quiz_service.QuizGenerationError)
def quiz_generation_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'code':4001,'message':str(exc),'data':None})
@app.get('/api/v1/health')
def health(): return {'code':0,'message':'ok','data':{'status':'healthy'}}
@app.post('/api/v1/quiz/generate')
def quiz(req: QuizRequest): return {'code':0,'message':'ok','data':quiz_service.generate_quiz(req)}
@app.post('/api/v1/report/generate')
def report(req: ReportRequest): return {'code':0,'message':'ok','data':report_service.generate_report(req)}
