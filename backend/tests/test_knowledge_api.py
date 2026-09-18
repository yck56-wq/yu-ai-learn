def test_knowledge_endpoints_require_login(client):
    assert client.get('/api/v1/knowledge/documents').status_code == 401
    assert client.post('/api/v1/knowledge/documents', files={'file': ('note.md', b'# hi', 'text/markdown')}).status_code == 401
    assert client.delete('/api/v1/knowledge/documents/doc_missing').status_code == 401


def test_knowledge_list_is_scoped_to_current_user(client, login):
    headers, _ = login('knowledge-owner')
    response = client.get('/api/v1/knowledge/documents', headers=headers)
    assert response.status_code == 200
    assert response.json()['data'] == []


def test_markdown_upload_list_delete_and_user_isolation(client, login, monkeypatch):
    from app.api.v1.routes import knowledge as knowledge_route

    vectors = {}
    class FakeEmbedding:
        def embed_documents(self, texts): return [[1.0, 0.0] for _ in texts]
        def embed_query(self, text): return [1.0, 0.0]
    class FakeStore:
        def __init__(self, user_id, embedding): self.user_id = user_id
        def add_documents(self, documents, document_id, metadata_extra=None):
            vectors[(self.user_id, document_id)] = documents
        def delete_document(self, document_id): vectors.pop((self.user_id, document_id), None)
    monkeypatch.setattr(knowledge_route, 'DashScopeEmbeddings', FakeEmbedding)
    monkeypatch.setattr(knowledge_route, 'PrivateVectorStore', FakeStore)
    owner_headers, _ = login('knowledge-owner-2')
    other_headers, _ = login('knowledge-other-2')
    response = client.post('/api/v1/knowledge/documents', headers=owner_headers,
                           files={'file': ('manual.md', b'# Internal\nKeep records.', 'text/markdown')})
    assert response.status_code == 200
    document_id = response.json()['data']['document_id']
    assert client.get('/api/v1/knowledge/documents', headers=other_headers).json()['data'] == []
    assert client.get('/api/v1/knowledge/documents', headers=owner_headers).json()['data'][0]['document_id'] == document_id
    assert client.delete('/api/v1/knowledge/documents/' + document_id, headers=other_headers).status_code == 404
    assert client.delete('/api/v1/knowledge/documents/' + document_id, headers=owner_headers).status_code == 200
    assert client.get('/api/v1/knowledge/documents', headers=owner_headers).json()['data'] == []


def test_upload_uses_client_original_name_and_rename_updates_vector_metadata(client, login, monkeypatch):
    from app.api.v1.routes import knowledge as knowledge_route

    renamed = []
    class FakeEmbedding: pass
    class FakeStore:
        def __init__(self, user_id, embedding): self.user_id = user_id
        def add_documents(self, documents, document_id, metadata_extra=None): pass
        def rename_document(self, document_id, file_name): renamed.append((document_id, file_name))
        def delete_document(self, document_id): pass
    monkeypatch.setattr(knowledge_route, 'DashScopeEmbeddings', FakeEmbedding)
    monkeypatch.setattr(knowledge_route, 'PrivateVectorStore', FakeStore)
    headers, _ = login('knowledge-rename')
    response = client.post('/api/v1/knowledge/documents', headers=headers,
                           data={'original_name': '企业文化笔记.md'},
                           files={'file': ('tmp-random-name.md', b'# Internal\nKeep records.', 'text/markdown')})
    assert response.status_code == 200
    assert response.json()['data']['original_name'] == '企业文化笔记.md'
    document_id = response.json()['data']['document_id']
    renamed_response = client.put('/api/v1/knowledge/documents/' + document_id, headers=headers,
                                  json={'name': '企业文化培训'})
    assert renamed_response.status_code == 200
    assert renamed_response.json()['data']['original_name'] == '企业文化培训.md'
    assert renamed == [(document_id, '企业文化培训.md')]


def test_upload_failure_rolls_back_vector_and_file(client, login, monkeypatch, tmp_path):
    from app.api.v1.routes import knowledge as knowledge_route
    from app.config import settings
    monkeypatch.setattr(settings, 'knowledge_storage_dir', str(tmp_path))
    class FakeEmbedding: pass
    class FailingStore:
        def __init__(self, user_id, embedding): self.deleted = False
        def add_documents(self, documents, document_id, metadata_extra=None): raise RuntimeError('provider')
        def delete_document(self, document_id): self.deleted = True
    monkeypatch.setattr(knowledge_route, 'DashScopeEmbeddings', FakeEmbedding)
    monkeypatch.setattr(knowledge_route, 'PrivateVectorStore', FailingStore)
    headers, _ = login('knowledge-rollback')
    response = client.post('/api/v1/knowledge/documents', headers=headers,
                           files={'file': ('rollback.md', b'rollback', 'text/markdown')})
    assert response.status_code == 503
    assert client.get('/api/v1/knowledge/documents', headers=headers).json()['data'] == []
    assert not [path for path in tmp_path.rglob('*') if path.is_file()]
