from langchain_core.documents import Document


def test_private_retrieval_returns_private_source_metadata(monkeypatch):
    from app import retrieval

    class FakeStore:
        def __init__(self, user_id, embedding): self.user_id = user_id
        def similarity_search(self, query, k=4, filter=None):
            return [Document(page_content='内部培训内容', metadata={'document_id': 'doc-1', 'file_name': '培训.md', 'page': 2})]
    monkeypatch.setattr(retrieval, 'PrivateVectorStore', FakeStore, raising=False)
    monkeypatch.setattr('app.vector_store.PrivateVectorStore', FakeStore)
    monkeypatch.setattr('app.services.embedding_service.DashScopeEmbeddings', lambda: object())
    sources = retrieval.retrieve_private_sources(7, '培训')
    assert sources[0].source_type == 'private'
    assert sources[0].document_id == 'doc-1'
    assert sources[0].page == 2


def test_private_retrieval_can_filter_document(monkeypatch):
    from app import retrieval
    captured = {}

    class FakeStore:
        def __init__(self, user_id, embedding): pass
        def similarity_search(self, query, k=4, document_id=None):
            captured['document_id'] = document_id
            return []

    monkeypatch.setattr(retrieval, 'PrivateVectorStore', FakeStore, raising=False)
    monkeypatch.setattr('app.vector_store.PrivateVectorStore', FakeStore)
    monkeypatch.setattr('app.services.embedding_service.DashScopeEmbeddings', lambda: object())
    assert retrieval.retrieve_private_sources(7, '培训', document_id='doc-1') == []
    assert captured['document_id'] == 'doc-1'


def test_document_specific_retrieval_does_not_mix_web_sources(monkeypatch):
    from app import retrieval
    private = retrieval.Source(id='p1', title='企业文化.md', snippet='内部资料', source_type='private', document_id='doc-1')
    monkeypatch.setattr(retrieval, 'retrieve_private_sources', lambda *args, **kwargs: [private])
    assert retrieval.retrieve_sources('企业文化', user_id=7, document_id='doc-1') == [private]


def test_quiz_request_accepts_optional_knowledge_document_id():
    from app.models import QuizRequest
    request = QuizRequest(user_input='企业文化', knowledge_document_id='doc-1')
    assert request.knowledge_document_id == 'doc-1'


def test_private_retrieval_failure_degrades_to_empty(monkeypatch):
    from app import retrieval
    monkeypatch.setattr('app.vector_store.PrivateVectorStore', lambda *args: (_ for _ in ()).throw(RuntimeError('hidden')))
    assert retrieval.retrieve_private_sources(7, 'anything') == []
