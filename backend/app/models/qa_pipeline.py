from dataclasses import dataclass, field
from typing import Any

from app.schemas.qa import AnswerSource, AnswerStatus, RelatedArtifact, ResolvedObject


@dataclass(slots=True)
class IntentResult:
    intent: str
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    needs_object: bool = True
    entities: dict[str, str] = field(default_factory=dict)   # 新增：存放抽取的实体，如 {"museum": "大英博物馆"}

@dataclass(slots=True)
class RetrievalResult:
    status: AnswerStatus
    facts: list[str] = field(default_factory=list)
    sources: list[AnswerSource] = field(default_factory=list)
    related_artifacts: list[RelatedArtifact] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GeneratedAnswer:
    status: AnswerStatus
    answer: str
    fact_content: str | None = None
    supplemental_content: str | None = None


@dataclass(slots=True)
class QAPipelineContext:
    question: str
    object_id: str | None
    session_id: str | None
    conversation_id: str | None
    user_id: int | None
    source_client: str | None
    intent: IntentResult | None = None
    resolved_object: ResolvedObject | None = None
    retrieval: RetrievalResult | None = None
    generated_answer: GeneratedAnswer | None = None
