from datetime import datetime

from pydantic import BaseModel


class KnowledgeDocument(BaseModel):
    document_id: str
    original_name: str
    extension: str
    file_size: int
    chunk_count: int
    status: str
    created_at: datetime | str


class KnowledgeRenameRequest(BaseModel):
    name: str
