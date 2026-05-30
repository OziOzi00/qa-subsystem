from app.models.qa_pipeline import QAPipelineContext
from app.schemas.qa import AskRequest, AskResponse, ResolvedObject
from app.services.answer_generator import answer_generator
from app.services.intent_recognizer import intent_recognizer
from app.services.knowledge_retriever import knowledge_retriever
from app.services.object_resolver import object_resolver
from app.services.qa_logger import qa_logger
from app.services.session_context import session_context_store


class QAService:
    """Orchestrate the full question answering pipeline.

    Pipeline:
    1. Normalize request question.
    2. Recognize question intent.
    3. Resolve artifact object_id from request, future entity extraction, or context.
    4. Retrieve facts from MySQL / Neo4j modules.
    5. Generate a user-facing answer with fact and supplemental sections.
    6. Record QA log and failed-question metadata.
    7. Return the unified response body used by Web, App, and demo frontend.
    """

    async def ask(self, request: AskRequest) -> AskResponse:
        context = QAPipelineContext(
            question=request.question.strip(),
            object_id=request.object_id.strip() if request.object_id else None,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            source_client=request.source_client,
        )

        context.intent = intent_recognizer.recognize(context.question)
        context.resolved_object = object_resolver.resolve(request, context.intent)
        context.retrieval = knowledge_retriever.retrieve(
            intent=context.intent,
            resolved_object=context.resolved_object,
            question=context.question,
        )
        context.generated_answer = answer_generator.generate(
            intent=context.intent,
            resolved_object=context.resolved_object,
            retrieval=context.retrieval,
        )

        qa_log_id = await qa_logger.record(context)
        await qa_logger.record_failed_if_needed(context)
        if context.resolved_object is not None:
            session_context_store.update_current_object(
                request.session_id or request.conversation_id,
                context.resolved_object,
            )
        session_context_store.append_turn(
            request.session_id or request.conversation_id,
            question=context.question,
            intent=context.intent.intent if context.intent else None,
            resolved_object=context.resolved_object,
            status=context.generated_answer.status.value if context.generated_answer else None,
        )

        return self._build_response(request, context, qa_log_id)

    def _build_response(
        self,
        request: AskRequest,
        context: QAPipelineContext,
        qa_log_id,
    ) -> AskResponse:
        intent = context.intent
        retrieval = context.retrieval
        generated_answer = context.generated_answer

        if intent is None or retrieval is None or generated_answer is None:
            raise RuntimeError("QA pipeline ended before all required steps completed.")

        resolved_object = context.resolved_object or ResolvedObject(
            objectId=None,
            title=None,
            resolveSource="unresolved",
        )
        if resolved_object.object_id == "DEMO_001" and resolved_object.title is None:
            resolved_object = resolved_object.model_copy(update={"title": "演示文物"})

        return AskResponse(
            qaLogId=qa_log_id,
            sessionId=request.session_id,
            status=generated_answer.status,
            intent=intent.intent,
            answer=generated_answer.answer,
            factContent=generated_answer.fact_content,
            supplementalContent=generated_answer.supplemental_content,
            resolvedObject=resolved_object,
            sources=retrieval.sources,
            relatedArtifacts=retrieval.related_artifacts,
            debug={
                "intentConfidence": intent.confidence,
                "matchedKeywords": intent.matched_keywords,
                "entities": intent.entities,
                "retrievalRaw": retrieval.raw,
                "recentContext": session_context_store.get_recent_turns(
                    request.session_id or request.conversation_id
                ),
            },
        )


qa_service = QAService()
