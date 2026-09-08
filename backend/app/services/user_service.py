import httpx
from fastapi import HTTPException

from ..config import settings
from ..core.auth import issue_token
from ..repositories import user_repository


async def login(pool, code):
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise HTTPException(503, '微信登录尚未配置')
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get('https://api.weixin.qq.com/sns/jscode2session', params={
                'appid': settings.wechat_app_id, 'secret': settings.wechat_app_secret,
                'js_code': code, 'grant_type': 'authorization_code',
            })
        if response.status_code != 200:
            raise HTTPException(502, '微信登录服务暂时不可用，请重试')
        data = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(502, '微信登录服务暂时不可用，请重试') from None
    if not isinstance(data, dict):
        raise HTTPException(502, '微信登录响应异常，请重试')
    if data.get('errcode') in (-1, 45011):
        raise HTTPException(503, '微信登录繁忙，请稍后重试')
    if data.get('errcode') in (40029, 40163):
        raise HTTPException(401, '登录凭证已失效，请重新登录')
    openid = data.get('openid')
    if data.get('errcode') or not isinstance(openid, str) or not 1 <= len(openid) <= 64:
        raise HTTPException(502, '微信登录响应异常，请重试')
    user = await user_repository.get_or_create(pool, openid)
    return {'token': issue_token(user['id']), 'user': user}
