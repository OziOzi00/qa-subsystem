from app.models.qa_pipeline import IntentResult
import re


def _normalize_entities(raw: dict) -> dict:
    """Normalize various entity key names to canonical keys expected by Neo4j queries.

    Canonical keys: 'museum', 'artifact_type', 'object_id', 'artifact_name', 'artist'
    Accepts camelCase, snake_case and some Chinese labels.
    """
    if not raw:
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if v is None:
            continue
        key = str(k).strip().lower()
        if key in {"museum", "museum_name", "博物馆", "馆名", "museumname"}:
            out["museum"] = str(v)
        elif key in {"artifact_type", "type", "artifacttype", "种类", "类别", "类型"}:
            out["artifact_type"] = str(v)
        elif key in {"object_id", "objectid", "id", "object"}:
            out["object_id"] = str(v)
        elif key in {"artifact_name", "name", "title", "title_zh", "名称", "文物名"}:
            out["artifact_name"] = str(v)
        elif key in {"artist", "creator", "author", "作者", "画家"}:
            out["artist"] = str(v)
        else:
            # keep other keys as-is (stringified)
            out[k] = str(v)
    return out


class IntentRecognizer:
    """Adapter recognizer that prefers Member4's backend implementation.

    Attempts to call `backend.intent_recognizer.recognize_intent` and maps its
    output to `IntentResult`. Falls back to the original lightweight rule-
    based recognizer if the backend module is unavailable.
    """

    # Mapping from numeric intent_type (backend) to pipeline intent string
    _type_map = {
        1: "artifact_museum",
        2: "artifact_period",
        3: "artifact_material",
        4: "artifact_type",
        5: "artifact_description",
        6: "artifact_artist",
        7: "artist_biography",
        8: "same_artist_artifacts",
        9: "same_dynasty_artifacts",
        10: "artifact_dimensions",
        11: "related_artifacts",
    }

    def __init__(self):
        # Lazy import of backend recognizer
        try:
            from backend.intent_recognizer import recognize_intent as _backend_recognize
        except Exception:
            _backend_recognize = None
        self._backend_recognize = _backend_recognize

    def recognize(self, question: str) -> IntentResult:
        # Try backend recognizer first
        if self._backend_recognize:
            try:
                res = self._backend_recognize(question, None)
                # res expected to be a dict with keys: intent_type, confidence, matched_keywords, extracted_entities
                intent_type = res.get("intent_type")
                intent_name = self._type_map.get(intent_type) if intent_type else "unknown"
                raw_entities = res.get("extracted_entities", {}) or {}
                entities = _normalize_entities(raw_entities)
                return IntentResult(
                    intent=intent_name,
                    confidence=float(res.get("confidence", 0.0)),
                    matched_keywords=res.get("matched_keywords", []),
                    needs_object=(intent_type is not None and intent_type in {1,2,3,4,5,6,7,8,9,10,11}),
                    entities=entities,
                )
            except Exception:
                # fall through to fallback recognizer
                pass

        # Fallback simple rule-based recognizer (keeps previous behavior)
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

        matched: list[str] = []
        for keyword, (intent, needs_object) in sorted(
            _keyword_mapping.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            if keyword in question:
                matched.append(keyword)
                # Try to extract simple museum mentions like 'XX博物馆' from the question
                entities: dict[str, str] = {}
                m = re.search(r"([\w\u4e00-\u9fa5]{2,30}博物馆)", question)
                if m:
                    entities["museum"] = m.group(1)
                return IntentResult(
                    intent=intent,
                    confidence=0.75,
                    matched_keywords=matched,
                    needs_object=needs_object,
                    entities=entities,
                )

        return IntentResult(
            intent="unknown",
            confidence=0.0,
            matched_keywords=[],
            needs_object=True,
        )


intent_recognizer = IntentRecognizer()
