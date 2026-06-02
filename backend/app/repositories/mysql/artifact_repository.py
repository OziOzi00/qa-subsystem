from dataclasses import dataclass, field
from typing import Protocol


class QueryClient(Protocol):
    def fetch_one(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> dict[str, object] | None: ...

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> list[dict[str, object]]: ...


@dataclass(frozen=True, slots=True)
class ArtistSummary:
    id: int
    name: str
    biography: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactDetail:
    id: int
    object_id: str
    title: str
    title_en: str | None = None
    time_period: str | None = None
    dynasty_name: str | None = None
    type: str | None = None
    material: str | None = None
    description: str | None = None
    dimensions: str | None = None
    museum_name: str | None = None
    museum_country: str | None = None
    museum_city: str | None = None
    detail_url: str | None = None
    image_url: str | None = None
    artists: list[ArtistSummary] = field(default_factory=list)


class ArtifactRepository:
    def __init__(self, client: QueryClient) -> None:
        self._client = client

    def find_by_object_id(self, object_id: str | None) -> ArtifactDetail | None:
        normalized_object_id = _clean(object_id)
        if normalized_object_id is None:
            return None

        row = self._client.fetch_one(
            """
            SELECT
                a.id,
                a.object_id,
                a.title_zh,
                a.title_en,
                a.time_period,
                d.name_zh AS dynasty_name_zh,
                a.type,
                a.material,
                a.description,
                a.dimensions,
                m.name AS museum_name,
                m.country AS museum_country,
                m.city AS museum_city,
                a.detail_url,
                a.image_url
            FROM artifacts a
            LEFT JOIN dynasties d ON d.id = a.dynasty_id
            LEFT JOIN museums m ON m.id = a.museum_id
            WHERE a.object_id = %s
            LIMIT 1
            """,
            (normalized_object_id,),
        )
        if row is None:
            return None

        artifact_id = int(row["id"])
        artists = self._find_artists(artifact_id)
        title = _clean(row.get("title_zh")) or _clean(row.get("title_en")) or normalized_object_id
        return ArtifactDetail(
            id=artifact_id,
            object_id=_clean(row.get("object_id")) or normalized_object_id,
            title=title,
            title_en=_clean(row.get("title_en")),
            time_period=_clean(row.get("time_period")),
            dynasty_name=_clean(row.get("dynasty_name_zh")),
            type=_clean(row.get("type")),
            material=_clean(row.get("material")),
            description=_clean(row.get("description")),
            dimensions=_clean(row.get("dimensions")),
            museum_name=_clean(row.get("museum_name")),
            museum_country=_clean(row.get("museum_country")),
            museum_city=_clean(row.get("museum_city")),
            detail_url=_clean(row.get("detail_url")),
            image_url=_clean(row.get("image_url")),
            artists=artists,
        )

    def find_museum_by_name(self, museum_name: str | None) -> dict[str, str | None] | None:
        normalized_name = _clean(museum_name)
        if normalized_name is None:
            return None

        row = self._client.fetch_one(
            """
            SELECT name, city, country
            FROM museums
            WHERE name = %s OR name LIKE CONCAT('%%', %s, '%%')
            ORDER BY CASE WHEN name = %s THEN 0 ELSE 1 END, id ASC
            LIMIT 1
            """,
            (normalized_name, normalized_name, normalized_name),
        )
        if row is None:
            return None

        return {
            "name": _clean(row.get("name")),
            "city": _clean(row.get("city")),
            "country": _clean(row.get("country")),
        }

    def _find_artists(self, artifact_id: int) -> list[ArtistSummary]:
        rows = self._client.fetch_all(
            """
            SELECT ar.id, ar.name_zh, ar.name_en, ar.biography
            FROM artifact_artist aa
            JOIN artists ar ON ar.id = aa.artist_id
            WHERE aa.artifact_id = %s
            ORDER BY ar.id ASC
            """,
            (artifact_id,),
        )
        artists: list[ArtistSummary] = []
        for row in rows:
            name = _clean(row.get("name_zh")) or _clean(row.get("name_en"))
            if name is None:
                continue
            artists.append(
                ArtistSummary(
                    id=int(row["id"]),
                    name=name,
                    biography=_clean(row.get("biography")),
                )
            )
        return artists

    def search_candidates(self, question: str) -> list[object]:
        from app.services.artifact_matcher import ArtifactCandidate

        question_text = _clean(question)
        if question_text is None:
            return []
        rows = self._client.fetch_all(
            """
            SELECT
                a.id,
                a.object_id,
                a.title_zh,
                a.title_en,
                a.type,
                a.material,
                a.dimensions,
                a.description,
                a.detail_url,
                a.image_url,
                m.name AS museum_name,
                d.name_zh AS dynasty_name_zh
            FROM artifacts a
            LEFT JOIN museums m ON m.id = a.museum_id
            LEFT JOIN dynasties d ON d.id = a.dynasty_id
            WHERE a.object_id IS NOT NULL
              AND TRIM(a.object_id) <> ''
              AND (
                (a.title_zh IS NOT NULL AND a.title_zh <> '' AND %s LIKE CONCAT('%%', a.title_zh, '%%'))
                OR
                (a.title_en IS NOT NULL AND a.title_en <> '' AND %s LIKE CONCAT('%%', a.title_en, '%%'))
              )
            ORDER BY a.id ASC
            LIMIT 10
            """,
            (question_text, question_text),
        )
        candidates: list[ArtifactCandidate] = []
        for row in rows:
            object_id = _clean(row.get("object_id"))
            if object_id is None:
                continue
            matched_name = _clean(row.get("title_zh")) or _clean(row.get("title_en"))
            if matched_name is None:
                continue
            candidates.append(
                ArtifactCandidate(
                    object_id=object_id,
                    title=matched_name,
                    matched_name=matched_name,
                    confidence=0.95 if len(matched_name) >= 4 else 0.75,
                    title_en=_clean(row.get("title_en")),
                    museum_name=_clean(row.get("museum_name")),
                    dynasty_name=_clean(row.get("dynasty_name_zh")),
                    artifact_type=_clean(row.get("type")),
                    material=_clean(row.get("material")),
                    dimensions=_clean(row.get("dimensions")),
                    description_preview=_preview(row.get("description")),
                    detail_url=_clean(row.get("detail_url")),
                    image_url=_clean(row.get("image_url")),
                )
            )
        return candidates

    def find_related_by_type(
        self,
        object_id: str,
        artifact_type: str | None,
        limit: int = 5,
    ) -> list[ArtifactDetail]:
        normalized_object_id = _clean(object_id)
        normalized_type = _clean(artifact_type)
        if normalized_object_id is None or normalized_type is None:
            return []

        rows = self._client.fetch_all(
            """
            SELECT
                a.id,
                a.object_id,
                a.title_zh,
                a.title_en,
                a.time_period,
                d.name_zh AS dynasty_name_zh,
                a.type,
                a.material,
                a.description,
                a.dimensions,
                m.name AS museum_name,
                m.country AS museum_country,
                m.city AS museum_city,
                a.detail_url,
                a.image_url
            FROM artifacts a
            LEFT JOIN dynasties d ON d.id = a.dynasty_id
            LEFT JOIN museums m ON m.id = a.museum_id
            WHERE a.object_id <> %s
              AND a.object_id IS NOT NULL
              AND TRIM(a.object_id) <> ''
              AND a.type = %s
            ORDER BY a.id ASC
            LIMIT %s
            """,
            (normalized_object_id, normalized_type, limit),
        )
        return [self._detail_from_row(row) for row in rows]

    def _detail_from_row(self, row: dict[str, object]) -> ArtifactDetail:
        normalized_object_id = _clean(row.get("object_id")) or str(row["id"])
        title = _clean(row.get("title_zh")) or _clean(row.get("title_en")) or normalized_object_id
        return ArtifactDetail(
            id=int(row["id"]),
            object_id=normalized_object_id,
            title=title,
            title_en=_clean(row.get("title_en")),
            time_period=_clean(row.get("time_period")),
            dynasty_name=_clean(row.get("dynasty_name_zh")),
            type=_clean(row.get("type")),
            material=_clean(row.get("material")),
            description=_clean(row.get("description")),
            dimensions=_clean(row.get("dimensions")),
            museum_name=_clean(row.get("museum_name")),
            museum_country=_clean(row.get("museum_country")),
            museum_city=_clean(row.get("museum_city")),
            detail_url=_clean(row.get("detail_url")),
            image_url=_clean(row.get("image_url")),
            artists=[],
        )


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _preview(value: object, max_length: int = 80) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length].rstrip() + "..."
