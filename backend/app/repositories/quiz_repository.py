import json

import aiomysql


async def save_quiz(pool, user_id, user_input, quiz):
    async with pool.acquire() as conn, conn.cursor() as cur:
        try:
            await cur.execute('''INSERT INTO quiz_sessions(quiz_id,user_id,title,summary,user_input,questions_json,sources_json,grounding_status)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)''', (quiz['quiz_id'], user_id, quiz['title'], quiz['summary'],
                                               user_input, json.dumps(quiz['questions'], ensure_ascii=False),
                                               json.dumps(quiz.get('sources', []), ensure_ascii=False), quiz.get('grounding_status', 'fallback')))
        except aiomysql.OperationalError as exc:
            if exc.args and exc.args[0] == 1054:
                await cur.execute('''INSERT INTO quiz_sessions(quiz_id,user_id,title,summary,user_input,questions_json)
                    VALUES(%s,%s,%s,%s,%s,%s)''', (quiz['quiz_id'], user_id, quiz['title'], quiz['summary'],
                                                   user_input, json.dumps(quiz['questions'], ensure_ascii=False)))
            else:
                raise


async def lock_quiz(conn, user_id, quiz_id):
    async with conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('SELECT * FROM quiz_sessions WHERE quiz_id=%s AND user_id=%s FOR UPDATE', (quiz_id, user_id))
        return await cur.fetchone()


async def saved_report(conn, user_id, quiz_id):
    async with conn.cursor() as cur:
        await cur.execute('SELECT report_json FROM reports WHERE quiz_id=%s AND user_id=%s', (quiz_id, user_id))
        row = await cur.fetchone()
        return json.loads(row[0]) if row else None


async def save_result(conn, user_id, quiz_id, records, report):
    correct = sum(record['is_correct'] for record in records)
    async with conn.cursor() as cur:
        # 先取得用户行写锁，再插入带 users 外键的子记录，避免不同轮次结算时共享锁升级死锁。
        # 后续任何写入失败仍由外层事务回滚 XP。
        await cur.execute('UPDATE users SET total_xp=total_xp+%s WHERE id=%s', (correct * 20, user_id))
        await cur.execute('''INSERT INTO answer_records(quiz_id,user_id,records_json,total_questions,correct_count,accuracy)
            VALUES(%s,%s,%s,%s,%s,%s)''', (quiz_id, user_id, json.dumps(records, ensure_ascii=False),
                                           len(records), correct, round(correct / len(records) * 100, 2)))
        await cur.execute('INSERT INTO reports(quiz_id,user_id,report_json) VALUES(%s,%s,%s)',
                          (quiz_id, user_id, json.dumps(report, ensure_ascii=False)))


async def history(pool, user_id, page, page_size):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('SELECT COUNT(*) AS total FROM reports WHERE user_id=%s', (user_id,))
        total = (await cur.fetchone())['total']
        await cur.execute('''SELECT q.quiz_id,q.title,a.accuracy,a.total_questions AS question_count,q.created_at
            FROM quiz_sessions q JOIN reports r ON r.quiz_id=q.quiz_id AND r.user_id=q.user_id
            JOIN answer_records a ON a.quiz_id=q.quiz_id AND a.user_id=q.user_id
            WHERE q.user_id=%s ORDER BY q.created_at DESC,q.id DESC LIMIT %s OFFSET %s''',
                          (user_id, page_size, (page - 1) * page_size))
        items = await cur.fetchall()
        for item in items:
            item['accuracy'] = float(item['accuracy'])
            item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        return {'items': list(items), 'total': total, 'page': page, 'page_size': page_size}


async def detail(pool, user_id, quiz_id):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        try:
            await cur.execute('''SELECT q.quiz_id,q.title,q.summary,q.questions_json,q.sources_json,q.grounding_status,a.records_json,r.report_json
            FROM quiz_sessions q JOIN reports r ON r.quiz_id=q.quiz_id AND r.user_id=q.user_id
            JOIN answer_records a ON a.quiz_id=q.quiz_id AND a.user_id=q.user_id
            WHERE q.user_id=%s AND q.quiz_id=%s''', (user_id, quiz_id))
        except aiomysql.OperationalError as exc:
            if not exc.args or exc.args[0] != 1054:
                raise
            await cur.execute('''SELECT q.quiz_id,q.title,q.summary,q.questions_json,a.records_json,r.report_json
                FROM quiz_sessions q JOIN reports r ON r.quiz_id=q.quiz_id AND r.user_id=q.user_id
                JOIN answer_records a ON a.quiz_id=q.quiz_id AND a.user_id=q.user_id
                WHERE q.user_id=%s AND q.quiz_id=%s''', (user_id, quiz_id))
        row = await cur.fetchone()
        if row is None:
            return None
        result = {'quiz_id': row['quiz_id'], 'title': row['title'], 'summary': row['summary'],
                'questions': json.loads(row['questions_json']), 'answer_records': json.loads(row['records_json']),
                'report': json.loads(row['report_json'])}
        if row.get('grounding_status'):
            result['grounding_status'] = row['grounding_status']
        if row.get('sources_json'):
            result['sources'] = json.loads(row['sources_json'])
        return result
