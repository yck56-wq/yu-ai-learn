from contextlib import asynccontextmanager

import aiomysql

from ..config import settings


@asynccontextmanager
async def lifespan(app):
    if len(settings.jwt_secret.encode()) < 32:
        raise RuntimeError('JWT signing key must contain at least 32 bytes.')
    try:
        pool = await aiomysql.create_pool(
            host=settings.mysql_host, port=settings.mysql_port,
            user=settings.mysql_user, password=settings.mysql_password,
            db=settings.mysql_database, charset='utf8mb4', autocommit=True,
            minsize=1, maxsize=10, connect_timeout=5, pool_recycle=1800,
            init_command="SET time_zone = '+08:00'",
        )
    except Exception:
        raise RuntimeError('Database connection failed; check server settings.') from None
    app.state.pool = pool
    try:
        yield
    finally:
        pool.close()
        await pool.wait_closed()


@asynccontextmanager
async def transaction(pool):
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            yield conn
            await conn.commit()
        except BaseException:
            await conn.rollback()
            raise
