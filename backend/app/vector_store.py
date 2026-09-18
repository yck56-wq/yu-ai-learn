from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from .config import settings


class PrivateVectorStore:
    def __init__(self, user_id: int, embedding: Any | None = None, persist_directory: str | None = None):
        from langchain_chroma import Chroma

        self.user_id = int(user_id)
        self.embedding = embedding
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self._store = Chroma(
            collection_name=f'user_{self.user_id}',
            embedding_function=embedding,
            persist_directory=self.persist_directory,
        )

    def add_documents(self, documents: list[Document], document_id: str, metadata_extra: dict[str, Any] | None = None) -> list[str]:
        ids = [f'{document_id}:{index}' for index in range(len(documents))]
        for document, chunk_id in zip(documents, ids):
            document.metadata = {
                **document.metadata,
                'user_id': str(self.user_id),
                'document_id': document_id,
                **(metadata_extra or {}),
            }
        if documents:
            self._store.add_documents(documents, ids=ids)
        return ids

    def similarity_search(self, query: str, k: int = 4, document_id: str | None = None) -> list[Document]:
        metadata_filter = {'user_id': str(self.user_id)}
        if document_id:
            metadata_filter['document_id'] = document_id
        return self._store.similarity_search(query, k=k, filter=metadata_filter)

    def delete_document(self, document_id: str) -> None:
        self._store.delete(where={'document_id': document_id})

    def rename_document(self, document_id: str, file_name: str) -> None:
        result = self._store._collection.get(where={'document_id': document_id}, include=['metadatas'])
        ids = result.get('ids', []) if isinstance(result, dict) else []
        metadatas = result.get('metadatas', []) if isinstance(result, dict) else []
        if not ids:
            return
        updated = [{**(metadata or {}), 'file_name': file_name} for metadata in metadatas]
        self._store._collection.update(ids=ids, metadatas=updated)

    def count(self, document_id: str | None = None) -> int:
        if document_id is None:
            return self._store._collection.count()
        result = self._store._collection.get(where={'document_id': document_id})
        return len(result.get('ids', [])) if isinstance(result, dict) else 0
