from fastapi import APIRouter, Depends, Request, Query

from ....core.auth import current_user
from ....repositories import user_repository, quiz_repository
from ....schemas.user import LoginRequest, ProfileUpdate
from ....services import user_service, history_service

router = APIRouter(prefix='/api/v1/user')


@router.post('/login')
async def login(body: LoginRequest, request: Request):
    data = await user_service.login(request.app.state.pool, body.code)
    return {'code': 0, 'message': 'ok', 'data': data}


@router.get('/profile')
async def profile(request: Request, user=Depends(current_user)):
    data = await user_repository.profile(request.app.state.pool, user['id'])
    return {'code': 0, 'message': 'ok', 'data': data}


@router.put('/profile')
async def update_profile(body: ProfileUpdate, request: Request, user=Depends(current_user)):
    data = await user_repository.update_profile(request.app.state.pool, user['id'], body.model_dump(exclude_unset=True))
    return {'code': 0, 'message': 'ok', 'data': data}


@router.get('/quizzes')
async def quizzes(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50), user=Depends(current_user)):
    data = await quiz_repository.history(request.app.state.pool, user['id'], page, page_size)
    return {'code': 0, 'message': 'ok', 'data': data}


@router.get('/quizzes/{quiz_id}')
async def quiz_detail(quiz_id: str, request: Request, user=Depends(current_user)):
    data = await history_service.detail(request.app.state.pool, user['id'], quiz_id)
    return {'code': 0, 'message': 'ok', 'data': data}
