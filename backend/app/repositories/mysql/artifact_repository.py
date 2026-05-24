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


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
