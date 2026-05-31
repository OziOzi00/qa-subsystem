import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from app.core.config import settings
from app.models.qa_pipeline import IntentResult, RetrievalResult
from app.schemas.qa import ResolvedObject

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LLMGenerationResult:
    content: str
    model: str


class OpenAICompatibleLLMClient:
    """Optional OpenAI-compatible client used for lightweight RAG generation.

    The client is deliberately optional: if the API key or base URL is missing,
    the QA system keeps using deterministic template answers.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self._base_url = _normalize_base_url(
            base_url if base_url is not None else settings.LLM_BASE_URL
        )
        self._model = model if model is not None else settings.LLM_MODEL
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.LLM_TIMEOUT_SECONDS
        )
        self._enabled = settings.LLM_ENABLED if enabled is None else enabled

    @property
    def is_configured(self) -> bool:
        return bool(self._enabled and self._api_key and self._base_url and self._model)

    def generate_supplement(
        self,
        *,
        question: str,
        intent: IntentResult,
        resolved_object: ResolvedObject,
        retrieval: RetrievalResult,
    ) -> LLMGenerationResult | None:
        if not self.is_configured or not retrieval.facts:
            return None

        payload = {
            "model": self._model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是海外藏中国文物知识问答系统的回答润色模块。"
                        "只能依据提供的检索事实生成补充说明，不能编造新的事实、年代、作者、数量或地点。"
                        "如果事实不足，请说明仍需补充数据。回答要简洁，使用中文。"
                    ),
                },
                {
                    "role": "user",
                    "content": _build_prompt(
                        question=question,
                        intent=intent,
                        resolved_object=resolved_object,
                        retrieval=retrieval,
                    ),
                },
            ],
        }

        request = urllib.request.Request(
            self._base_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("LLM supplement generation failed: %s", exc)
            return None

        try:
            data = json.loads(body)
            content = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("LLM response cannot be parsed: %s", exc)
            return None

        if not content:
            return None
        return LLMGenerationResult(content=content, model=self._model)


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed
    return f"{trimmed}/chat/completions"


def _build_prompt(
    *,
    question: str,
    intent: IntentResult,
    resolved_object: ResolvedObject,
    retrieval: RetrievalResult,
) -> str:
    facts = "\n".join(f"- {fact}" for fact in retrieval.facts)
    sources = "\n".join(
        f"- {source.source_type.value}: {source.source_name}"
        + (f"，链接：{source.detail_url}" if source.detail_url else "")
        for source in retrieval.sources
    )
    object_text = (
        f"{resolved_object.title or ''} ({resolved_object.object_id})"
        if resolved_object.object_id
        else "当前问题不依赖单件文物"
    )
    return (
        f"用户问题：{question}\n"
        f"识别意图：{intent.intent}\n"
        f"文物对象：{object_text}\n"
        f"检索事实：\n{facts}\n"
        f"数据来源：\n{sources or '- 暂无来源说明'}\n\n"
        "请基于上述事实生成 1-3 句补充说明。不要输出未在事实中出现的新信息。"
    )


llm_client = OpenAICompatibleLLMClient()
