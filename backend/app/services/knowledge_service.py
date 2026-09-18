import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.md', '.markdown'}


class KnowledgeError(Exception):
    def __init__(self, message: str, status_code: int = 422, error_code: str = 'KNOWLEDGE_INVALID'):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


@dataclass
class ParsedKnowledge:
    extension: str
    documents: list[Document]
    chunks: list[Document]


def extension_for(filename: str) -> str:
    extension = Path(filename or '').suffix.lower()
    if extension == '.markdown':
        extension = '.md'
    if extension not in SUPPORTED_EXTENSIONS:
        raise KnowledgeError('仅支持 PDF、DOCX 或 Markdown 文件。', 422, 'UNSUPPORTED_FILE_TYPE')
    return extension


def _load(path: str, extension: str) -> list[Document]:
    try:
        if extension == '.pdf':
            from langchain_community.document_loaders import PyPDFLoader
            return PyPDFLoader(path).load()
        if extension == '.docx':
            from langchain_community.document_loaders import Docx2txtLoader
            return Docx2txtLoader(path).load()
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader
            return UnstructuredMarkdownLoader(path).load()
        except (ImportError, ModuleNotFoundError):
            from langchain_community.document_loaders import TextLoader
            return TextLoader(path, encoding='utf-8').load()
    except KnowledgeError:
        raise
    except Exception:
        logger.warning('document_parse_failed extension=%s', extension)
        raise KnowledgeError('文件无法读取或解析失败。', 422, 'DOCUMENT_PARSE_FAILED') from None


def parse_and_split(content: bytes, filename: str, *, max_file_bytes: int | None = None,
                    max_text_chars: int | None = None, chunk_size: int | None = None,
                    chunk_overlap: int | None = None, max_chunks: int | None = None) -> ParsedKnowledge:
    extension = extension_for(filename)
    max_file_bytes = settings.knowledge_max_file_bytes if max_file_bytes is None else max_file_bytes
    max_text_chars = settings.knowledge_max_text_chars if max_text_chars is None else max_text_chars
    chunk_size = settings.knowledge_chunk_size if chunk_size is None else chunk_size
    chunk_overlap = settings.knowledge_chunk_overlap if chunk_overlap is None else chunk_overlap
    max_chunks = settings.knowledge_max_chunks if max_chunks is None else max_chunks
    if len(content) > max_file_bytes:
        raise KnowledgeError('文件超过大小限制。', 413, 'FILE_TOO_LARGE')
    if not content:
        raise KnowledgeError('文件内容不能为空。', 422, 'EMPTY_FILE')
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(prefix='knowledge-', suffix=extension, delete=False) as temp:
            temp.write(content)
            temp_path = temp.name
        documents = _load(temp_path, extension)
        text_length = sum(len((document.page_content or '').strip()) for document in documents)
        if text_length == 0:
            raise KnowledgeError('文件没有可用文本内容。', 422, 'EMPTY_TEXT')
        if text_length > max_text_chars:
            raise KnowledgeError('文件文本超过处理上限。', 413, 'TEXT_TOO_LARGE')
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_documents(documents)
        if not chunks:
            raise KnowledgeError('文件没有可用文本内容。', 422, 'EMPTY_TEXT')
        if len(chunks) > max_chunks:
            raise KnowledgeError('文件切片数量超过处理上限。', 413, 'TOO_MANY_CHUNKS')
        return ParsedKnowledge(extension=extension, documents=documents, chunks=chunks)
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def document_storage_path(user_id: int, document_id: str, extension: str) -> Path:
    return Path(settings.knowledge_storage_dir) / str(user_id) / f'{document_id}{extension}'


def new_document_id() -> str:
    return f'doc_{uuid4().hex}'
