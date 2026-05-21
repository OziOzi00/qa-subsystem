from dataclasses import dataclass
from datetime import datetime

from app.schemas.qa import ResolvedObject


@dataclass(slots=True)
class SessionObjectContext:
    object_id: str
    title: str | None
    updated_at: datetime


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
        )


session_context_store = SessionContextStore()
