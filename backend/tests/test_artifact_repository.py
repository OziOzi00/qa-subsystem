from app.repositories.mysql.artifact_repository import ArtifactRepository


class FakeMySQLClient:
    def __init__(self) -> None:
        self.fetch_one_calls: list[tuple[str, tuple[object, ...] | None]] = []
        self.fetch_all_calls: list[tuple[str, tuple[object, ...] | None]] = []

    def fetch_one(self, sql: str, params: tuple[object, ...] | None = None):
        self.fetch_one_calls.append((sql, params))
        return {
            "id": 10,
            "object_id": " MET_123 ",
            "title_zh": " 青花瓷 ",
            "title_en": "Blue Porcelain",
            "time_period": "Ming dynasty",
            "dynasty_name_zh": "明",
            "type": " Ceramics ",
            "material": " porcelain ",
            "description": "A porcelain artifact.",
            "dimensions": " H. 10 cm ",
            "museum_name": "British Museum",
            "museum_country": "United Kingdom",
            "museum_city": "London",
            "detail_url": " ",
            "image_url": "",
        }

    def fetch_all(self, sql: str, params: tuple[object, ...] | None = None):
        self.fetch_all_calls.append((sql, params))
        return [
            {
                "id": 7,
                "name_zh": "佚名",
                "name_en": "",
                "biography": " ",
            }
        ]


def test_find_by_object_id_maps_artifact_detail_and_normalizes_blank_values() -> None:
    client = FakeMySQLClient()
    repository = ArtifactRepository(client)

    artifact = repository.find_by_object_id("MET_123")

    assert artifact is not None
    assert artifact.id == 10
    assert artifact.object_id == "MET_123"
    assert artifact.title == "青花瓷"
    assert artifact.type == "Ceramics"
    assert artifact.material == "porcelain"
    assert artifact.dimensions == "H. 10 cm"
    assert artifact.detail_url is None
    assert artifact.image_url is None
    assert artifact.museum_name == "British Museum"
    assert artifact.dynasty_name == "明"
    assert artifact.artists[0].name == "佚名"
    assert artifact.artists[0].biography is None
    assert client.fetch_one_calls[0][1] == ("MET_123",)
    assert client.fetch_all_calls[0][1] == (10,)


def test_find_by_object_id_returns_none_for_blank_object_id_without_query() -> None:
    client = FakeMySQLClient()
    repository = ArtifactRepository(client)

    artifact = repository.find_by_object_id("  ")

    assert artifact is None
    assert client.fetch_one_calls == []
    assert client.fetch_all_calls == []
