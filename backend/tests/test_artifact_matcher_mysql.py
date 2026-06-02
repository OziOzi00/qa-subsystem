from app.services.artifact_matcher import ArtifactCandidate, ArtifactMatcher


class FakeCandidateRepository:
    def __init__(self, candidates: list[ArtifactCandidate]) -> None:
        self.candidates = candidates
        self.questions: list[str] = []

    def search_candidates(self, question: str) -> list[ArtifactCandidate]:
        self.questions.append(question)
        return self.candidates


def test_match_uses_repository_candidates_and_filters_blank_object_ids() -> None:
    repository = FakeCandidateRepository(
        [
            ArtifactCandidate(
                object_id="MET_123",
                title="青花瓷",
                matched_name="青花瓷",
                confidence=0.95,
            ),
            ArtifactCandidate(
                object_id=" ",
                title="缺失编号文物",
                matched_name="缺失编号文物",
                confidence=0.95,
            ),
        ]
    )
    matcher = ArtifactMatcher(candidate_repository=repository)

    candidates = matcher.match("青花瓷是什么材质？")

    assert [candidate.object_id for candidate in candidates] == ["MET_123"]
    assert repository.questions == ["青花瓷是什么材质？"]


def test_match_deduplicates_multiple_repository_candidates() -> None:
    repository = FakeCandidateRepository(
        [
            ArtifactCandidate(
                object_id="MET_123",
                title="青花瓷",
                matched_name="瓷",
                confidence=0.75,
            ),
            ArtifactCandidate(
                object_id="MET_123",
                title="青花瓷",
                matched_name="青花瓷",
                confidence=0.95,
            ),
            ArtifactCandidate(
                object_id="MET_456",
                title="白瓷",
                matched_name="白瓷",
                confidence=0.75,
            ),
        ]
    )
    matcher = ArtifactMatcher(candidate_repository=repository)

    candidates = matcher.match("青花瓷和白瓷有什么区别？")

    assert [(candidate.object_id, candidate.matched_name) for candidate in candidates] == [
        ("MET_123", "青花瓷"),
        ("MET_456", "白瓷"),
    ]


def test_match_filters_short_subsumed_candidate_names() -> None:
    repository = FakeCandidateRepository(
        [
            ArtifactCandidate(
                object_id="A_1",
                title="Rhino horn cup",
                matched_name="Rhino horn cup",
                confidence=0.95,
            ),
            ArtifactCandidate(
                object_id="A_2",
                title="Horn",
                matched_name="Horn",
                confidence=0.75,
            ),
        ]
    )
    matcher = ArtifactMatcher(candidate_repository=repository)

    candidates = matcher.match("Tell me about Rhino horn cup")

    assert [(candidate.object_id, candidate.matched_name) for candidate in candidates] == [
        ("A_1", "Rhino horn cup"),
    ]


def test_candidate_response_includes_disambiguation_metadata() -> None:
    candidate = ArtifactCandidate(
        object_id="A_1",
        title="Vase",
        matched_name="Vase",
        confidence=0.95,
        museum_name="Philadelphia Museum of Art",
        dynasty_name="Qing dynasty",
        artifact_type="Container",
        detail_url="https://example.org/artifact/A_1",
    )

    assert candidate.to_response_candidate() == {
        "objectId": "A_1",
        "title": "Vase",
        "matchedName": "Vase",
        "confidence": 0.95,
        "museumName": "Philadelphia Museum of Art",
        "dynastyName": "Qing dynasty",
        "artifactType": "Container",
        "detailUrl": "https://example.org/artifact/A_1",
    }


def test_match_without_repository_keeps_demo_catalog() -> None:
    matcher = ArtifactMatcher()

    candidates = matcher.match("演示文物是什么材质？")

    assert candidates[0].object_id == "DEMO_001"
