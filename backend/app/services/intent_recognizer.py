from app.models.qa_pipeline import IntentResult


class IntentRecognizer:
    """Rule-based intent recognizer for the first runnable scaffold.

    Member 4 can replace this implementation with a richer rule set or an LLM
    classifier while keeping the same `recognize` method contract.
    """

    _keyword_mapping: dict[str, tuple[str, bool]] = {
        "收藏": ("artifact_museum", True),
        "现藏": ("artifact_museum", True),
        "哪里": ("artifact_museum", True),
        "哪家博物馆": ("artifact_museum", True),
        "博物馆": ("artifact_museum", True),
        "年代": ("artifact_period", True),
        "朝代": ("artifact_period", True),
        "时期": ("artifact_period", True),
        "材质": ("artifact_material", True),
        "材料": ("artifact_material", True),
        "类型": ("artifact_type", True),
        "类别": ("artifact_type", True),
        "介绍": ("artifact_description", True),
        "讲讲": ("artifact_description", True),
        "作者": ("artifact_artist", True),
        "生平": ("artist_biography", True),
        "同一作者": ("same_artist_artifacts", True),
        "还有哪些作品": ("same_artist_artifacts", True),
        "同一朝代": ("same_dynasty_artifacts", True),
        "代表性文物": ("same_dynasty_artifacts", False),
        "尺寸": ("artifact_dimensions", True),
        "规格": ("artifact_dimensions", True),
        "重量": ("artifact_dimensions", True),
        "相关": ("related_artifacts", True),
        "相似": ("related_artifacts", True),
        "推荐": ("related_artifacts", True),
        "多少件": ("statistics_count", False),
        "数量": ("statistics_count", False),
        "最多": ("statistics_top_museum", False),
        "在哪个城市": ("museum_city", False),
    }

    def recognize(self, question: str) -> IntentResult:
        matched: list[str] = []
        for keyword, (intent, needs_object) in sorted(
            self._keyword_mapping.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if keyword in question:
                matched.append(keyword)
                return IntentResult(
                    intent=intent,
                    confidence=0.75,
                    matched_keywords=matched,
                    needs_object=needs_object,
                )

        return IntentResult(
            intent="unknown",
            confidence=0.0,
            matched_keywords=[],
            needs_object=True,
        )


intent_recognizer = IntentRecognizer()
