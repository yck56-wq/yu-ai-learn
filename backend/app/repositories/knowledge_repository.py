import aiomysql


async def create(pool, *, document_id, user_id, original_name, extension, file_size, storage_key, chunk_count, status='ready'):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('''INSERT INTO knowledge_documents
            (document_id,user_id,original_name,extension,file_size,storage_key,chunk_count,status)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)''',
            (document_id, user_id, original_name, extension, file_size, storage_key, chunk_count, status))
        await cur.execute('''SELECT document_id,original_name,extension,file_size,chunk_count,status,created_at
            FROM knowledge_documents WHERE document_id=%s AND user_id=%s''', (document_id, user_id))
        return await cur.fetchone()


async def list_for_user(pool, user_id):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('''SELECT document_id,original_name,extension,file_size,chunk_count,status,created_at
            FROM knowledge_documents WHERE user_id=%s ORDER BY created_at DESC''', (user_id,))
        return await cur.fetchall()


async def get_for_user(pool, user_id, document_id):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('''SELECT document_id,original_name,extension,file_size,storage_key,chunk_count,status,created_at
            FROM knowledge_documents WHERE user_id=%s AND document_id=%s''', (user_id, document_id))
        return await cur.fetchone()


async def delete_for_user(pool, user_id, document_id):
    async with pool.acquire() as conn, conn.cursor() as cur:
        await cur.execute('DELETE FROM knowledge_documents WHERE user_id=%s AND document_id=%s', (user_id, document_id))
        return cur.rowcount > 0


async def rename_for_user(pool, user_id, document_id, original_name):
    async with pool.acquire() as conn, conn.cursor(aiomysql.DictCursor) as cur:
        await cur.execute('UPDATE knowledge_documents SET original_name=%s WHERE user_id=%s AND document_id=%s',
                          (original_name, user_id, document_id))
        await cur.execute('''SELECT document_id,original_name,extension,file_size,chunk_count,status,created_at
            FROM knowledge_documents WHERE document_id=%s AND user_id=%s''', (document_id, user_id))
        return await cur.fetchone()
