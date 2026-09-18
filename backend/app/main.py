import logging
import inspect

import pymysql
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .core.auth import current_user
from .core.db import lifespan
from .api.v1.routes.user import router as user_router
from .api.v1.routes.knowledge import router as knowledge_router
from .models import QuizRequest, ReportRequest
from starlette.concurrency import run_in_threadpool
from .services import quiz_service, history_service
from .repositories import quiz_repository
app=FastAPI(title='开卷有戏 API', lifespan=lifespan)
app.include_router(user_router)
app.include_router(knowledge_router)
# httpx INFO 日志会包含微信 GET 查询串，禁止输出其中的凭证。
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                        content={'code': exc.status_code, 'message': exc.detail, 'data': None})

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(status_code=422, content={'code': 422, 'message': '请求参数不合法，请检查后重试', 'data': None})

@app.exception_handler(pymysql.MySQLError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={'code': 503, 'message': '数据服务暂时不可用，请稍后重试', 'data': None})
@app.exception_handler(quiz_service.QuizGenerationError)
def quiz_generation_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'code': 4001, 'error_code': exc.error_code,
                        'message': str(exc), 'data': None})
@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.getLogger(__name__).warning('unexpected_error error_type=%s', type(exc).__name__)
    return JSONResponse(status_code=503, content={'code': 503, 'message': '服务暂时不可用，请稍后重试', 'data': None})
@app.get('/api/v1/health')
def health(): return {'code':0,'message':'ok','data':{'status':'healthy'}}
@app.post('/api/v1/quiz/generate')
async def quiz(req: QuizRequest, request: Request, user=Depends(current_user)):
    generator = quiz_service.generate_quiz
    args = (req, user['id']) if 'user_id' in inspect.signature(generator).parameters else (req,)
    data = await run_in_threadpool(generator, *args)
    await quiz_repository.save_quiz(request.app.state.pool, user['id'], req.user_input, data)
    return {'code':0,'message':'ok','data':data}
@app.post('/api/v1/report/generate')
async def report(req: ReportRequest, request: Request, user=Depends(current_user)):
    data = await history_service.settle(request.app.state.pool, user['id'], req)
    return {'code':0,'message':'ok','data':data}
