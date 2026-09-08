from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings
from ..repositories.user_repository import get_user

bearer = HTTPBearer(auto_error=False)


def issue_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({'user_id': user_id, 'iat': now, 'exp': now + timedelta(days=7)},
                      settings.jwt_secret, algorithm='HS256')


async def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    unauthorized = HTTPException(401, '登录已失效，请重新登录', headers={'WWW-Authenticate': 'Bearer'})
    if credentials is None:
        raise unauthorized
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=['HS256'],
                            options={'require': ['user_id', 'exp']})
        user_id = claims['user_id']
        if type(user_id) is not int or user_id <= 0:
            raise unauthorized
    except (jwt.InvalidTokenError, TypeError, ValueError, OverflowError):
        raise unauthorized from None
    user = await get_user(request.app.state.pool, user_id)
    if user is None:
        raise unauthorized
    return user
