import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


class EmbeddingConfigurationError(RuntimeError):
    pass


class DashScopeEmbeddings:
    """Small LangChain-compatible adapter around DashScope text-embedding-v4."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key if api_key is not None else settings.embedding_api_key
        self.model = model or settings.embedding_model

    def _call(self, texts: list[str], text_type: str) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingConfigurationError('Embedding 服务尚未配置。')
        try:
            import dashscope
            dashscope.api_key = self.api_key
            response = dashscope.TextEmbedding.call(
                model=self.model,
                input=texts,
                text_type=text_type,
            )
            status = getattr(response, 'status_code', 200)
            payload: Any = response if isinstance(response, dict) else getattr(response, 'output', None)
            if hasattr(response, 'output'):
                payload = response.output
            if status != 200:
                raise RuntimeError('embedding provider rejected request')
            items = payload.get('embeddings', []) if isinstance(payload, dict) else []
            items = sorted(items, key=lambda item: item.get('text_index', 0))
            vectors = [item.get('embedding') for item in items if isinstance(item, dict)]
            if len(vectors) != len(texts) or any(not isinstance(vector, list) for vector in vectors):
                raise RuntimeError('embedding provider returned invalid vectors')
            return vectors
        except EmbeddingConfigurationError:
            raise
        except Exception as exc:
            logger.warning('embedding_failed error_type=%s', type(exc).__name__)
            raise RuntimeError('Embedding 服务暂时不可用。') from None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._call(texts, 'document')

    def embed_query(self, text: str) -> list[float]:
        return self._call([text], 'query')[0]
