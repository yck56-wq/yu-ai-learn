from fastapi import APIRouter, Depends, Request, Query, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from ....core.auth import current_user
from ....config import settings
from ....repositories import user_repository, quiz_repository
from ....schemas.user import LoginRequest, ProfileUpdate
from ....services import user_service, history_service, avatar_service

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


@router.post('/avatar')
async def upload_avatar(request: Request, file: UploadFile, user=Depends(current_user)):
    form = await request.form()
    try:
        fields = ProfileUpdate(nickname=form['nickname']).model_dump(exclude_unset=True) if 'nickname' in form else {}
    except ValidationError:
        raise HTTPException(422, '昵称不合法，请检查后重试') from None
    path = await run_in_threadpool(avatar_service.store_avatar, await file.read(avatar_service.MAX_BYTES + 1))
    base_url = (settings.public_base_url or str(request.base_url)).rstrip('/')
    fields['avatar_url'] = f'{base_url}/api/v1/user/avatars/{path.name}'
    data = await user_repository.update_profile(request.app.state.pool, user['id'], fields)
    return {'code': 0, 'message': 'ok', 'data': data}


@router.get('/avatars/{filename}')
async def avatar_image(filename: str):
    path = await run_in_threadpool(avatar_service.avatar_path, filename)
    return FileResponse(path, media_type='image/png', headers={'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'public, max-age=31536000, immutable'})


@router.get('/quizzes/{quiz_id}')
async def quiz_detail(quiz_id: str, request: Request, user=Depends(current_user)):
    data = await history_service.detail(request.app.state.pool, user['id'], quiz_id)
    return {'code': 0, 'message': 'ok', 'data': data}
