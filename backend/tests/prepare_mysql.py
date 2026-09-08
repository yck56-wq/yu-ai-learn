"""核对业务表并准备专用测试库；不修改业务库表或数据。"""
from pathlib import Path
import json
import pymysql
from dotenv import dotenv_values


def connection(database=None):
    env = dotenv_values(Path(__file__).resolve().parents[1] / '.env')
    return pymysql.connect(host=env['MYSQL_HOST'], port=int(env['MYSQL_PORT']),
                           user=env['MYSQL_USER'], password=env['MYSQL_PASSWORD'],
                           database=database, charset='utf8mb4', autocommit=True)


def prepare():
    env = dotenv_values(Path(__file__).resolve().parents[1] / '.env')
    with connection(env['MYSQL_DATABASE']) as conn, conn.cursor() as cur:
        cur.execute('SELECT VERSION()')
        version = cur.fetchone()[0]
        cur.execute('SHOW TABLES')
        tables = [row[0] for row in cur.fetchall()]
        expected = {'users', 'quiz_sessions', 'answer_records', 'reports'}
        if not expected.issubset(tables):
            raise RuntimeError('Business schema incomplete')
        columns = {}
        for table in sorted(expected):
            cur.execute('SHOW COLUMNS FROM `' + table + '`')
            columns[table] = [row[0] for row in cur.fetchall()]
        print(json.dumps({'mysql_version': version, 'business_tables': columns}))
    # 明确固定专用测试库；只在此库执行原始建表语句。
    with connection() as conn, conn.cursor() as cur:
        cur.execute('CREATE DATABASE IF NOT EXISTS yu_ai_learn_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    sql = (Path(__file__).resolve().parents[2] / 'sql/001_user_system.sql').read_text(encoding='utf-8')
    with connection('yu_ai_learn_test') as conn, conn.cursor() as cur:
        for statement in sql.split(';'):
            if statement.strip().startswith('CREATE TABLE'):
                cur.execute(statement)
    print('Dedicated test schema ready.')


if __name__ == '__main__':
    try:
        prepare()
    except Exception as exc:
        print('Database verification failed: ' + type(exc).__name__)
        raise SystemExit(1) from None
