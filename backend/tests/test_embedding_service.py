import pytest
from dashscope.api_entities.dashscope_response import DashScopeAPIResponse
from dashscope.client.base_api import BaseApi

from app.services.embedding_service import DashScopeEmbeddings


@pytest.mark.parametrize('text_type', ['document', 'query'])
def test_embedding_uses_sdk_text_array_contract(monkeypatch, text_type):
    """Keep real SDK input conversion so nested input.texts is rejected."""
    requests = []

    def send(cls, **kwargs):
        requests.append(kwargs)
        texts = kwargs['input']['texts']
        if not isinstance(texts, list):
            return DashScopeAPIResponse(status_code=400, code='InvalidParameter',
                                       message='input.texts should be array', output=None)
        return DashScopeAPIResponse(status_code=200, output={
            'embeddings': [{'text_index': i, 'embedding': [float(i), 1.0]}
                           for i in reversed(range(len(texts)))],
        })

    monkeypatch.setattr(BaseApi, 'call', classmethod(send))
    embedding = DashScopeEmbeddings(api_key='test-placeholder')
    if text_type == 'document':
        result = embedding.embed_documents(['企业文化', '安全生产'])
        assert result == [[0.0, 1.0], [1.0, 1.0]]
        assert requests[0]['input'] == {'texts': ['企业文化', '安全生产']}
    else:
        assert embedding.embed_query('企业文化') == [0.0, 1.0]
        assert requests[0]['input'] == {'texts': ['企业文化']}
    assert requests[0]['text_type'] == text_type
