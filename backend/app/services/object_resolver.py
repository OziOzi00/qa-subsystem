from app.models.qa_pipeline import IntentResult
from app.schemas.qa import AskRequest, ResolvedObject
from app.services.artifact_matcher import artifact_matcher
from app.services.session_context import session_context_store


class ObjectResolver:
    """Resolve the current artifact object for a question.

    Priority:
    1. Unique artifact name mentioned in the question.
    2. Explicit object_id from URL/body, used by Web/App integration.
    3. Session current_object_id for follow-up questions.
    4. Candidate list or clarification prompt.
    """

    def resolve(self, request: AskRequest, intent: IntentResult) -> ResolvedObject:
        if not intent.needs_object:
            return ResolvedObject(
                objectId=None,
                title=None,
                resolveSource="not_required_for_intent",
            )

        question_candidates = artifact_matcher.match(request.question.strip())
        if len(question_candidates) == 1:
            candidate = question_candidates[0]
            return ResolvedObject(
                objectId=candidate.object_id,
                title=candidate.title,
                resolveSource="question_entity",
                candidates=[candidate.to_response_candidate()],
            )

        if len(question_candidates) > 1:
            return ResolvedObject(
                objectId=None,
                title=None,
                resolveSource="ambiguous_question_entity",
                candidates=[
                    candidate.to_response_candidate()
                    for candidate in question_candidates
                ],
            )

        request_object_id = request.object_id.strip() if request.object_id else None
        if request_object_id:
            return ResolvedObject(
                objectId=request_object_id,
                title=None,
                resolveSource="request_object_id",
            )

        session_key = request.session_id or request.conversation_id
        session_object = session_context_store.get_current_object(session_key)
        if session_object is not None:
            return session_object

        return ResolvedObject(
            objectId=None,
            title=None,
            resolveSource="unresolved",
        )


object_resolver = ObjectResolver()
