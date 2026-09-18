from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from ....config import settings
from ....core.auth import current_user
from ....repositories import knowledge_repository
from ....services.embedding_service import DashScopeEmbeddings, EmbeddingConfigurationError
from ....services.knowledge_service import KnowledgeError, document_storage_path, new_document_id, parse_and_split
from ....schemas.knowledge import KnowledgeRenameRequest
from ....vector_store import PrivateVectorStore

router = APIRouter(prefix='/api/v1/knowledge', tags=['knowledge'])


def _safe_name(value: str) -> str:
    return Path(value or 'document').name[:255] or 'document'


@router.post('/documents')
async def upload_document(request: Request, file: UploadFile, original_name: str | None = Form(None), user=Depends(current_user)):
    original_name = _safe_name(original_name or file.filename or '')
    content = await file.read(settings.knowledge_max_file_bytes + 1)
    document_id = new_document_id()
    storage_path = None
    store = None
    success = False
    try:
        parsed = await run_in_threadpool(parse_and_split, content, original_name)
        storage_path = document_storage_path(user['id'], document_id, parsed.extension)
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        storage_path.write_bytes(content)
        for chunk in parsed.chunks:
            chunk.metadata = {**chunk.metadata, 'file_name': original_name}
            if chunk.metadata.get('page') is None:
                chunk.metadata.pop('page', None)
        embedding = DashScopeEmbeddings()
        store = await run_in_threadpool(PrivateVectorStore, user['id'], embedding)
        await run_in_threadpool(store.add_documents, parsed.chunks, document_id)
        row = await knowledge_repository.create(request.app.state.pool, document_id=document_id, user_id=user['id'],
                                                original_name=original_name, extension=parsed.extension,
                                                file_size=len(content), storage_key=str(storage_path),
                                                chunk_count=len(parsed.chunks))
        success = True
        return {'code': 0, 'message': 'ok', 'data': row}
    except KnowledgeError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    except EmbeddingConfigurationError:
        if store:
            await run_in_threadpool(store.delete_document, document_id)
        raise HTTPException(503, '知识库服务尚未配置，请联系管理员。') from None
    except Exception:
        if store:
            try:
                await run_in_threadpool(store.delete_document, document_id)
            except Exception:
                pass
        raise HTTPException(503, '知识库处理暂时不可用，请稍后重试。') from None
    finally:
        if storage_path and not success and storage_path.exists():
            try:
                storage_path.unlink()
            except OSError:
                pass


@router.get('/documents')
async def list_documents(request: Request, user=Depends(current_user)):
    data = await knowledge_repository.list_for_user(request.app.state.pool, user['id'])
    return {'code': 0, 'message': 'ok', 'data': data}


@router.delete('/documents/{document_id}')
async def delete_document(document_id: str, request: Request, user=Depends(current_user)):
    row = await knowledge_repository.get_for_user(request.app.state.pool, user['id'], document_id)
    if row is None:
        raise HTTPException(404, '文档不存在')
    try:
        store = await run_in_threadpool(PrivateVectorStore, user['id'], None)
        await run_in_threadpool(store.delete_document, document_id)
    except EmbeddingConfigurationError:
        raise HTTPException(503, '知识库服务尚未配置，请联系管理员。') from None
    except Exception:
        raise HTTPException(503, '知识库删除暂时不可用，请稍后重试。') from None
    await knowledge_repository.delete_for_user(request.app.state.pool, user['id'], document_id)
    try:
        Path(row['storage_key']).unlink(missing_ok=True)
    except OSError:
        pass
    return {'code': 0, 'message': 'ok', 'data': {'document_id': document_id}}


@router.put('/documents/{document_id}')
async def rename_document(document_id: str, payload: KnowledgeRenameRequest, request: Request, user=Depends(current_user)):
    row = await knowledge_repository.get_for_user(request.app.state.pool, user['id'], document_id)
    if row is None:
        raise HTTPException(404, '文档不存在')
    name = _safe_name(payload.name).strip()
    if not name:
        raise HTTPException(422, '名称不能为空')
    suffix = Path(name).suffix.lower()
    extension = str(row['extension']).lower()
    if suffix and suffix != extension:
        raise HTTPException(422, '不能修改文档格式')
    stem = Path(name).stem if suffix else name
    original_name = _safe_name(stem[:240] + extension)
    try:
        store = await run_in_threadpool(PrivateVectorStore, user['id'], None)
        await run_in_threadpool(store.rename_document, document_id, original_name)
        updated = await knowledge_repository.rename_for_user(request.app.state.pool, user['id'], document_id, original_name)
    except EmbeddingConfigurationError:
        raise HTTPException(503, '知识库服务尚未配置，请联系管理员。') from None
    except Exception:
        raise HTTPException(503, '知识库重命名暂时不可用，请稍后重试。') from None
    return {'code': 0, 'message': 'ok', 'data': updated}
