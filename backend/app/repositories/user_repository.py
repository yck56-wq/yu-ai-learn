import aiomysql


async def get_user(pool, user_id):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('SELECT id,nickname,avatar_url,total_xp FROM users WHERE id=%s', (user_id,))
        return await cur.fetchone()


async def get_or_create(pool, openid):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute("INSERT INTO users(openid,nickname,avatar_url) VALUES(%s,'学习者','') ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id)", (openid,))
        await cur.execute('SELECT id,nickname,avatar_url,total_xp FROM users WHERE openid=%s', (openid,))
        return await cur.fetchone()


async def profile(pool, user_id):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('''SELECT u.id,u.nickname,u.avatar_url,u.total_xp,
            COUNT(r.id) AS quiz_count,COALESCE(SUM(a.correct_count),0) AS correct_count,
            COALESCE(ROUND(SUM(a.correct_count)/NULLIF(SUM(a.total_questions),0)*100,2),0) AS average_accuracy
            FROM users u LEFT JOIN reports r ON r.user_id=u.id
            LEFT JOIN answer_records a ON a.quiz_id=r.quiz_id AND a.user_id=u.id
            WHERE u.id=%s GROUP BY u.id''', (user_id,))
        result = await cur.fetchone()
        if result:
            result['correct_count'] = int(result['correct_count'])
            result['average_accuracy'] = float(result['average_accuracy'])
        return result


async def update_profile(pool, user_id, fields):
    # 字段名称仅来自严格的 Pydantic 模型，不接收任意 SQL 标识符。
    assignments = ','.join(name + '=%s' for name in ('nickname', 'avatar_url') if name in fields)
    values = [fields[name] for name in ('nickname', 'avatar_url') if name in fields]
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute('UPDATE users SET ' + assignments + ' WHERE id=%s', (*values, user_id))
    return await profile(pool, user_id)
