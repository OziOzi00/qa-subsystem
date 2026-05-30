from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.schemas.qa import ResolvedObject


@dataclass(slots=True)
class SessionTurn:
    question: str
    intent: str | None
    object_id: str | None
    status: str | None
    created_at: datetime


@dataclass(slots=True)
class SessionObjectContext:
    object_id: str
    title: str | None
    updated_at: datetime
    recent_turns: list[SessionTurn]


class SessionContextStore:
    """Temporary in-memory context store for the runnable scaffold.

    The course requirement asks for recent context support. This store gives the
    leader-owned `object_id` fallback a working shape before Member 4 persists
    the latest five rounds in `qa_session`.
    """

    def __init__(self) -> None:
        self._objects: dict[str, SessionObjectContext] = {}

    def get_current_object(self, session_key: str | None) -> ResolvedObject | None:
        if not session_key:
            return None
        context = self._objects.get(session_key)
        if context is None:
            return None
        return ResolvedObject(
            objectId=context.object_id,
            title=context.title,
            resolveSource="session_context",
        )

    def update_current_object(
        self,
        session_key: str | None,
        resolved_object: ResolvedObject,
    ) -> None:
        if not session_key or not resolved_object.object_id:
            return
        self._objects[session_key] = SessionObjectContext(
            object_id=resolved_object.object_id,
            title=resolved_object.title,
            updated_at=datetime.utcnow(),
            recent_turns=self._objects.get(session_key).recent_turns[-4:]
            if session_key in self._objects
            else [],
        )

    def append_turn(
        self,
        session_key: str | None,
        question: str,
        intent: str | None,
        resolved_object: ResolvedObject | None,
        status: str | None,
    ) -> None:
        if not session_key:
            return
        current = self._objects.get(session_key)
        object_id = resolved_object.object_id if resolved_object else None
        title = resolved_object.title if resolved_object else None
        if current is None and not object_id:
            return

        turns = list(current.recent_turns) if current else []
        turns.append(
            SessionTurn(
                question=question,
                intent=intent,
                object_id=object_id or (current.object_id if current else None),
                status=status,
                created_at=datetime.utcnow(),
            )
        )
        turns = turns[-5:]

        if object_id:
            self._objects[session_key] = SessionObjectContext(
                object_id=object_id,
                title=title,
                updated_at=datetime.utcnow(),
                recent_turns=turns,
            )
        elif current is not None:
            current.recent_turns = turns
            current.updated_at = datetime.utcnow()

    def get_recent_turns(self, session_key: str | None) -> list[dict[str, Any]]:
        if not session_key:
            return []
        context = self._objects.get(session_key)
        if context is None:
            return []
        return [
            {
                "question": turn.question,
                "intent": turn.intent,
                "objectId": turn.object_id,
                "status": turn.status,
                "createdAt": turn.created_at.isoformat(),
            }
            for turn in context.recent_turns
        ]


session_context_store = SessionContextStore()
