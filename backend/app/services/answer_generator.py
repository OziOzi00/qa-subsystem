from app.models.qa_pipeline import GeneratedAnswer, IntentResult, RetrievalResult
from app.schemas.qa import AnswerStatus, ResolvedObject


class AnswerGenerator:
    """Generate user-facing answers from retrieved facts."""

    _unsupported_answer = "当前问题暂未匹配到已支持的文物问答类型。"

    def generate(
        self,
        intent: IntentResult,
        resolved_object: ResolvedObject,
        retrieval: RetrievalResult,
    ) -> GeneratedAnswer:
        if retrieval.status == AnswerStatus.NEED_CLARIFICATION:
            if resolved_object.resolve_source == "ambiguous_question_entity":
                names = "、".join(
                    str(candidate.get("title"))
                    for candidate in resolved_object.candidates
                    if candidate.get("title")
                )
                return GeneratedAnswer(
                    status=AnswerStatus.NEED_CLARIFICATION,
                    answer=f"识别到多个可能的文物对象：{names}。请从候选列表中选择一件文物后继续提问。",
                )

            return GeneratedAnswer(
                status=AnswerStatus.NEED_CLARIFICATION,
                answer="请补充文物名称，或从文物详情页进入问答页面后再提问。",
            )

        if intent.intent == "unknown":
            return GeneratedAnswer(
                status=AnswerStatus.UNSUPPORTED,
                answer=self._unsupported_answer,
            )

        if retrieval.status == AnswerStatus.NO_DATA:
            return GeneratedAnswer(
                status=AnswerStatus.NO_DATA,
                answer="暂无相关数据。",
            )

        fact_content = "\n".join(retrieval.facts) if retrieval.facts else None
        answer = self._render_template(intent.intent, resolved_object, retrieval)
        return GeneratedAnswer(
            status=AnswerStatus.ANSWERED,
            answer=answer,
            fact_content=fact_content,
            supplemental_content="该回答由模板根据知识库事实生成；后续接入大语言模型时，补充性描述将在此单独标注。",
        )

    def _render_template(
        self,
        intent: str,
        resolved_object: ResolvedObject,
        retrieval: RetrievalResult,
    ) -> str:
        if retrieval.facts:
            return retrieval.facts[0]
        if resolved_object.object_id:
            return f"已识别文物 {resolved_object.object_id}，但暂无可展示的事实数据。"
        return "暂无相关数据。"


answer_generator = AnswerGenerator()
