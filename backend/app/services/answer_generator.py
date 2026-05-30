from app.models.qa_pipeline import GeneratedAnswer, IntentResult, RetrievalResult
from app.schemas.qa import AnswerStatus, ResolvedObject


class AnswerGenerator:
    """Generate user-facing answers from retrieved facts and templates."""

    _unsupported_answer = (
        "当前问题暂未匹配到已支持的文物问答类型。"
        "你可以询问文物收藏地、年代、材质、类型、介绍、作者、尺寸或相关文物。"
    )

    _no_data_templates: dict[str, str] = {
        "artifact_museum": "暂无该文物收藏地数据。",
        "artifact_period": "暂无该文物年代数据。",
        "artifact_material": "暂无该文物材质数据。",
        "artifact_type": "暂无该文物类型数据。",
        "artifact_description": "暂无该文物介绍数据。",
        "artifact_artist": "暂无该文物作者数据。",
        "artist_biography": "暂无该文物作者生平数据。",
        "same_artist_artifacts": "暂无同一作者作品数据。",
        "same_dynasty_artifacts": "暂无同一朝代文物数据。",
        "artifact_dimensions": "暂无该文物尺寸与规格数据。",
        "related_artifacts": "暂无相关文物推荐数据。",
        "statistics_count": "暂无该博物馆收藏数量统计数据。",
        "statistics_top_museum": "暂无该类型文物收藏统计数据。",
        "museum_city": "暂无该博物馆所在城市数据。",
    }

    def generate(
        self,
        intent: IntentResult,
        resolved_object: ResolvedObject,
        retrieval: RetrievalResult,
    ) -> GeneratedAnswer:
        if retrieval.status == AnswerStatus.NEED_CLARIFICATION:
            return self._clarification_answer(resolved_object)

        if intent.intent == "unknown":
            return GeneratedAnswer(
                status=AnswerStatus.UNSUPPORTED,
                answer=self._unsupported_answer,
            )

        if retrieval.status == AnswerStatus.NO_DATA:
            return GeneratedAnswer(
                status=AnswerStatus.NO_DATA,
                answer=self._no_data_templates.get(intent.intent, "暂无相关数据。"),
            )

        fact_content = "\n".join(retrieval.facts) if retrieval.facts else None
        answer = self._render_template(resolved_object, retrieval)
        return GeneratedAnswer(
            status=AnswerStatus.ANSWERED,
            answer=answer,
            fact_content=fact_content,
            supplemental_content=(
                "该回答由系统根据 MySQL 或 Neo4j 中的已确认事实生成；"
                "如后续接入大语言模型，补充性描述会在此字段中单独标注。"
            ),
        )

    def _clarification_answer(self, resolved_object: ResolvedObject) -> GeneratedAnswer:
        if resolved_object.resolve_source == "ambiguous_question_entity":
            names = "、".join(
                str(candidate.get("title"))
                for candidate in resolved_object.candidates
                if candidate.get("title")
            )
            return GeneratedAnswer(
                status=AnswerStatus.NEED_CLARIFICATION,
                answer=(
                    f"识别到多个可能的文物对象：{names}。"
                    "请从候选列表中选择一件文物后继续提问。"
                ),
            )

        return GeneratedAnswer(
            status=AnswerStatus.NEED_CLARIFICATION,
            answer="请补充文物名称，或从文物详情页进入问答页面后再提问。",
        )

    def _render_template(
        self,
        resolved_object: ResolvedObject,
        retrieval: RetrievalResult,
    ) -> str:
        if retrieval.facts:
            return retrieval.facts[0]
        if resolved_object.object_id:
            return f"已识别文物 {resolved_object.object_id}，但暂无可展示的事实数据。"
        return "暂无相关数据。"


answer_generator = AnswerGenerator()
