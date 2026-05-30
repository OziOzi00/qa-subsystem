import re
from dataclasses import dataclass
from typing import Any

from app.models.qa_pipeline import IntentResult


@dataclass(frozen=True, slots=True)
class IntentRule:
    intent: str
    keywords: tuple[str, ...]
    needs_object: bool = True
    confidence: float = 0.78


class IntentRecognizer:
    """Rule-based recognizer for the required QA intents.

    This implementation keeps the contract simple for integration: it returns
    the intent code, whether an artifact object is required, matched keywords,
    and extracted entities used by the Neo4j statistical queries.
    """

    _simple_rules: tuple[IntentRule, ...] = (
        IntentRule(
            "same_artist_artifacts",
            ("同一作者", "同作者", "还有哪些作品", "其他作品", "同一位作者"),
        ),
        IntentRule(
            "same_dynasty_artifacts",
            ("同一朝代", "同朝代", "同一年代", "这个朝代还有", "该朝代还有"),
        ),
        IntentRule(
            "related_artifacts",
            ("相关文物", "相似文物", "相关推荐", "推荐文物", "推荐一下"),
        ),
        IntentRule(
            "artist_biography",
            ("作者生平", "作者介绍", "作者简介", "生平", "经历"),
        ),
        IntentRule(
            "artifact_dimensions",
            ("尺寸", "规格", "大小", "高度", "宽度", "长度", "重量"),
        ),
        IntentRule(
            "artifact_description",
            ("介绍", "简介", "说明", "讲讲", "背景", "内容", "详细信息"),
        ),
        IntentRule(
            "artifact_museum",
            ("收藏地", "收藏在哪里", "现藏", "馆藏", "哪个博物馆", "哪家博物馆", "收藏于"),
        ),
        IntentRule(
            "artifact_period",
            ("年代", "朝代", "时期", "时代", "什么时候", "哪个朝代"),
        ),
        IntentRule(
            "artifact_material",
            ("材质", "材料", "质地", "什么做的", "由什么制成"),
        ),
        IntentRule(
            "artifact_type",
            ("类型", "类别", "种类", "品类", "属于什么"),
        ),
        IntentRule(
            "artifact_artist",
            ("作者", "创作者", "谁画的", "谁写的", "谁创作"),
        ),
    )

    _representative_dynasty_pattern = re.compile(
        r"(?P<dynasty>[\u4e00-\u9fa5A-Za-z]{1,20}(?:朝|代|时期|Dynasty|dynasty))"
        r".{0,12}(?:代表性文物|代表文物)"
    )
    _museum_count_pattern = re.compile(
        r"(?P<museum>[\u4e00-\u9fa5A-Za-z·\s]{2,40}?博物馆)"
        r".{0,20}(?:收藏|藏有|馆藏).{0,20}(?:多少|几|数量|总数)"
    )
    _top_museum_pattern = re.compile(
        r"(?:收藏|馆藏)?(?P<artifact_type>[\u4e00-\u9fa5A-Za-z]{1,20})"
        r"(?:类)?(?:文物)?.{0,10}(?:最多|最多的).{0,10}博物馆"
    )
    _museum_city_pattern = re.compile(
        r"(?P<museum>[\u4e00-\u9fa5A-Za-z·\s]{2,40}?博物馆).{0,12}(?:城市|在哪|位于)"
    )

    def recognize(self, question: str) -> IntentResult:
        text = _normalize_question(question)
        if not text:
            return self._unknown()

        statistical = self._recognize_statistical_or_multihop(text)
        if statistical is not None:
            return statistical

        for rule in self._simple_rules:
            matched = [keyword for keyword in rule.keywords if keyword in text]
            if matched:
                return IntentResult(
                    intent=rule.intent,
                    confidence=rule.confidence,
                    matched_keywords=matched,
                    entities=self._extract_common_entities(text),
                    needs_object=rule.needs_object,
                )

        return self._unknown()

    def _recognize_statistical_or_multihop(
        self,
        text: str,
    ) -> IntentResult | None:
        top_match = self._top_museum_pattern.search(text)
        if top_match:
            artifact_type = _clean_entity(top_match.group("artifact_type"))
            if artifact_type:
                return IntentResult(
                    intent="statistics_top_museum",
                    confidence=0.9,
                    matched_keywords=["最多", "博物馆"],
                    entities={"artifact_type": artifact_type},
                    needs_object=False,
                )

        count_match = self._museum_count_pattern.search(text)
        if count_match:
            museum = _clean_entity(count_match.group("museum"))
            if museum:
                return IntentResult(
                    intent="statistics_count",
                    confidence=0.9,
                    matched_keywords=["收藏", "多少"],
                    entities={"museum": museum},
                    needs_object=False,
                )

        dynasty_match = self._representative_dynasty_pattern.search(text)
        if dynasty_match:
            dynasty = _clean_entity(dynasty_match.group("dynasty"))
            return IntentResult(
                intent="same_dynasty_artifacts",
                confidence=0.84,
                matched_keywords=["代表性文物"],
                entities={"dynasty": dynasty} if dynasty else {},
                needs_object=False,
            )

        city_match = self._museum_city_pattern.search(text)
        if city_match and not _contains_artifact_pronoun(text):
            museum = _clean_entity(city_match.group("museum"))
            if museum:
                return IntentResult(
                    intent="museum_city",
                    confidence=0.86,
                    matched_keywords=["博物馆", "城市"],
                    entities={"museum": museum},
                    needs_object=False,
                )

        if "博物馆" in text and ("城市" in text or "位于" in text):
            return IntentResult(
                intent="museum_city",
                confidence=0.78,
                matched_keywords=["博物馆", "城市"],
                entities={},
                needs_object=True,
            )

        return None

    def _extract_common_entities(self, text: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        museum_match = re.search(r"([\u4e00-\u9fa5A-Za-z·\s]{2,40}?博物馆)", text)
        if museum_match and not _contains_artifact_pronoun(museum_match.group(1)):
            museum = _clean_entity(museum_match.group(1))
            if museum:
                entities["museum"] = museum
        return entities

    def _unknown(self) -> IntentResult:
        return IntentResult(
            intent="unknown",
            confidence=0.0,
            matched_keywords=[],
            entities={},
            needs_object=True,
        )


def _normalize_question(question: str) -> str:
    return question.strip().replace("？", "?").replace("　", " ")


def _clean_entity(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip(" ?？。，“”\"'：:；;、")
    cleaned = re.sub(r"^(请问|我想知道|想知道|帮我查一下|查询)", "", cleaned)
    cleaned = re.sub(r"(一共|总共)$", "", cleaned)
    return cleaned.strip() or None


def _contains_artifact_pronoun(text: str) -> bool:
    return any(pronoun in text for pronoun in ("这件文物", "该文物", "这个文物", "它", "此文物"))


intent_recognizer = IntentRecognizer()
