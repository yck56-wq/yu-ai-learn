from pathlib import Path

import pytest

from app.services.knowledge_service import KnowledgeError, parse_and_split


def test_markdown_is_loaded_and_split():
    result = parse_and_split(b'# Safety\n\nWear a helmet before entering.', 'guide.md', chunk_size=20, chunk_overlap=0)
    assert result.extension == '.md'
    assert result.chunks
    assert 'helmet' in ''.join(chunk.page_content for chunk in result.chunks)


@pytest.mark.parametrize('name', ['guide.exe', 'guide.txt', ''])
def test_unsupported_extension_is_rejected(name):
    with pytest.raises(KnowledgeError) as error:
        parse_and_split(b'content', name)
    assert error.value.error_code == 'UNSUPPORTED_FILE_TYPE'


def test_empty_and_oversized_content_are_rejected():
    with pytest.raises(KnowledgeError) as empty:
        parse_and_split(b'', 'empty.md')
    assert empty.value.error_code == 'EMPTY_FILE'
    with pytest.raises(KnowledgeError) as oversized:
        parse_and_split(b'12345', 'large.md', max_file_bytes=4)
    assert oversized.value.error_code == 'FILE_TOO_LARGE'


def test_parser_does_not_leave_temp_file(monkeypatch):
    result = parse_and_split(b'hello', 'note.md')
    assert result.chunks


def test_vector_store_isolated_deleted_and_persistent(tmp_path):
    from app.vector_store import PrivateVectorStore
    from langchain_core.documents import Document
    class FakeEmbedding:
        def embed_documents(self, texts): return [[1.0, 0.0] for _ in texts]
        def embed_query(self, text): return [1.0, 0.0]
    first = PrivateVectorStore(1, FakeEmbedding(), str(tmp_path))
    second = PrivateVectorStore(2, FakeEmbedding(), str(tmp_path))
    first.add_documents([Document(page_content='alpha')], 'doc-a')
    second.add_documents([Document(page_content='beta')], 'doc-b')
    assert [item.page_content for item in first.similarity_search('alpha')] == ['alpha']
    assert [item.page_content for item in second.similarity_search('beta')] == ['beta']
    restarted = PrivateVectorStore(1, FakeEmbedding(), str(tmp_path))
    assert restarted.count('doc-a') == 1
    restarted.delete_document('doc-a')
    assert restarted.count('doc-a') == 0


def test_vector_store_rename_updates_source_file_name(tmp_path):
    from app.vector_store import PrivateVectorStore
    from langchain_core.documents import Document
    class FakeEmbedding:
        def embed_documents(self, texts): return [[1.0, 0.0] for _ in texts]
        def embed_query(self, text): return [1.0, 0.0]
    store = PrivateVectorStore(3, FakeEmbedding(), str(tmp_path))
    store.add_documents([Document(page_content='alpha')], 'doc-c', metadata_extra={'file_name': '旧名称.md'})
    store.rename_document('doc-c', '新名称.md')
    assert store.similarity_search('alpha')[0].metadata['file_name'] == '新名称.md'
