from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Option(BaseModel): key: str; text: str
class Source(BaseModel):
    id: str; title: str; url: str = ''; publisher: str = ''; snippet: str = ''
    published_at: str | None = None; fetched_at: str | None = None
    source_type: Literal['web', 'private'] = 'web'
    document_id: str | None = None
    file_name: str | None = None
    page: int | None = None
class Question(BaseModel):
    id: str; type: Literal['single','multiple','judge']; stem: str; options: list[Option]; answer: list[str]; explanation: str; knowledge_point: str; difficulty: Literal['easy','medium','hard']; source_ids: list[str] = Field(default_factory=list)
class Quiz(BaseModel): quiz_id: str; title: str; summary: str; questions: list[Question]; sources: list[Source] = Field(default_factory=list); grounding_status: Literal['grounded','fallback'] = 'fallback'
class QuizRequest(BaseModel): user_input: str = Field(min_length=1,max_length=5000); question_count: int = Field(default=5,ge=3,le=5); difficulty: Literal['mixed','easy','medium','hard']='mixed'; knowledge_document_id: str | None = Field(default=None, min_length=1, max_length=128)
class AnswerRecord(BaseModel): question_id: str; selected_answers: list[str]; duration_ms: int = Field(ge=0)
class ReportRequest(BaseModel): quiz_id: str; topic: str; questions: list[Question]; answer_records: list[AnswerRecord]
class Report(BaseModel): accuracy: int; mastered_points: list[str]; weak_points: list[str]; three_line_summary: list[str]; advice: list[str]; share_quote: str
