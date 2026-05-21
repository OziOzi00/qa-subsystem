from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArtifactCandidate:
    object_id: str
    title: str
    matched_name: str
    confidence: float

    def to_response_candidate(self) -> dict[str, object]:
        return {
            "objectId": self.object_id,
            "title": self.title,
            "matchedName": self.matched_name,
            "confidence": self.confidence,
        }


class ArtifactMatcher:
    """Match artifact names mentioned in the question.

    This scaffold uses a small demo catalog so the resolver can be tested before
    MySQL is connected. Member 2 and Member 4 can replace `match` with a real
    artifact-name search backed by `artifacts.title` and aliases.
    """

    _demo_catalog: tuple[dict[str, object], ...] = (
        {
            "object_id": "DEMO_001",
            "title": "演示文物",
            "aliases": ("演示文物", "测试瓷器", "青花演示瓷器"),
        },
        {
            "object_id": "DEMO_002",
            "title": "相关演示文物",
            "aliases": ("相关演示文物", "演示相关文物"),
        },
    )

    def match(self, question: str) -> list[ArtifactCandidate]:
        candidates: list[ArtifactCandidate] = []
        for item in self._demo_catalog:
            aliases = item["aliases"]
            assert isinstance(aliases, tuple)
            for alias in aliases:
                if alias in question:
                    candidates.append(
                        ArtifactCandidate(
                            object_id=str(item["object_id"]),
                            title=str(item["title"]),
                            matched_name=alias,
                            confidence=self._confidence(alias),
                        )
                    )
                    break

        return self._deduplicate(candidates)

    def _confidence(self, matched_name: str) -> float:
        if len(matched_name) >= 4:
            return 0.95
        return 0.75

    def _deduplicate(
        self,
        candidates: list[ArtifactCandidate],
    ) -> list[ArtifactCandidate]:
        best_by_object_id: dict[str, ArtifactCandidate] = {}
        for candidate in candidates:
            current = best_by_object_id.get(candidate.object_id)
            if current is None or candidate.confidence > current.confidence:
                best_by_object_id[candidate.object_id] = candidate
        return list(best_by_object_id.values())


artifact_matcher = ArtifactMatcher()
