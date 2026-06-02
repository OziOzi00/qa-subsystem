from dataclasses import dataclass
from typing import Protocol

from app.db.mysql import MySQLClient, MySQLConfig, get_mysql_dsn
from app.repositories.mysql.artifact_repository import ArtifactRepository


@dataclass(frozen=True, slots=True)
class ArtifactCandidate:
    object_id: str
    title: str
    matched_name: str
    confidence: float
    title_en: str | None = None
    museum_name: str | None = None
    dynasty_name: str | None = None
    artifact_type: str | None = None
    material: str | None = None
    dimensions: str | None = None
    description_preview: str | None = None
    detail_url: str | None = None
    image_url: str | None = None

    def to_response_candidate(self) -> dict[str, object]:
        candidate = {
            "objectId": self.object_id,
            "title": self.title,
            "matchedName": self.matched_name,
            "confidence": self.confidence,
        }
        optional_fields = {
            "titleEn": self.title_en,
            "museumName": self.museum_name,
            "dynastyName": self.dynasty_name,
            "artifactType": self.artifact_type,
            "material": self.material,
            "dimensions": self.dimensions,
            "descriptionPreview": self.description_preview,
            "detailUrl": self.detail_url,
            "imageUrl": self.image_url,
        }
        candidate.update(
            {key: value for key, value in optional_fields.items() if value}
        )
        return candidate


class CandidateRepository(Protocol):
    def search_candidates(self, question: str) -> list[ArtifactCandidate]: ...


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

    def __init__(self, candidate_repository: CandidateRepository | None = None) -> None:
        self._candidate_repository = candidate_repository

    def match(self, question: str) -> list[ArtifactCandidate]:
        if self._candidate_repository is not None:
            try:
                return self._deduplicate(
                    self._filter_subsumed_matches([
                        candidate
                        for candidate in self._candidate_repository.search_candidates(
                            question
                        )
                        if candidate.object_id.strip()
                    ])
                )
            except Exception:
                return []

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

    def _filter_subsumed_matches(
        self,
        candidates: list[ArtifactCandidate],
    ) -> list[ArtifactCandidate]:
        result: list[ArtifactCandidate] = []
        matched_names = [candidate.matched_name for candidate in candidates]
        for candidate in candidates:
            matched_name = candidate.matched_name
            normalized_name = matched_name.lower()
            is_subsumed = any(
                matched_name != other
                and normalized_name in other.lower()
                and len(other) > len(matched_name)
                for other in matched_names
            )
            if not is_subsumed:
                result.append(candidate)
        return result

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


def _build_default_matcher() -> ArtifactMatcher:
    mysql_dsn = get_mysql_dsn()
    if not mysql_dsn:
        return ArtifactMatcher()
    try:
        client = MySQLClient(MySQLConfig.from_dsn(mysql_dsn))
    except ValueError:
        return ArtifactMatcher()
    return ArtifactMatcher(candidate_repository=ArtifactRepository(client))


artifact_matcher = _build_default_matcher()
