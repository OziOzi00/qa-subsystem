from fastapi import APIRouter, HTTPException, Query

from app.schemas.admin import PaginatedResponse, ReviewTaskActionRequest
from app.services.admin_service import admin_service

router = APIRouter()


def _paginated(items: list[dict], total: int, page: int, page_size: int) -> PaginatedResponse:
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/admin/qa/logs", response_model=PaginatedResponse)
async def get_qa_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(None),
    intent: str | None = Query(None),
    keyword: str | None = Query(None),
    start_time: str | None = Query(None, alias="startTime"),
    end_time: str | None = Query(None, alias="endTime"),
) -> PaginatedResponse:
    """Query QA logs with pagination and filters."""
    items, total = await admin_service.query_logs(
        page=page, page_size=page_size,
        status=status, intent=intent, keyword=keyword,
        start_time=start_time, end_time=end_time,
    )
    return _paginated(items, total, page, page_size)


@router.get("/admin/qa/feedback", response_model=PaginatedResponse)
async def get_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    feedback_type: str | None = Query(None, alias="feedbackType"),
    keyword: str | None = Query(None),
) -> PaginatedResponse:
    """Query user feedback records with pagination."""
    items, total = await admin_service.query_feedback(
        page=page, page_size=page_size,
        feedback_type=feedback_type, keyword=keyword,
    )
    return _paginated(items, total, page, page_size)


@router.get("/admin/qa/failed-questions", response_model=PaginatedResponse)
async def get_failed_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    failure_type: str | None = Query(None, alias="failureType"),
    status: str | None = Query(None),
    intent: str | None = Query(None),
    keyword: str | None = Query(None),
) -> PaginatedResponse:
    """Query failed questions with pagination and filters."""
    items, total = await admin_service.query_failed_questions(
        page=page, page_size=page_size,
        failure_type=failure_type, status=status,
        intent=intent, keyword=keyword,
    )
    return _paginated(items, total, page, page_size)


@router.get("/admin/qa/review-tasks", response_model=PaginatedResponse)
async def get_review_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    task_status: str | None = Query(None, alias="taskStatus"),
    review_result: str | None = Query(None, alias="reviewResult"),
) -> PaginatedResponse:
    """Query review tasks with pagination and filters."""
    items, total = await admin_service.query_review_tasks(
        page=page, page_size=page_size,
        task_status=task_status, review_result=review_result,
    )
    return _paginated(items, total, page, page_size)


@router.post("/admin/qa/review-tasks/{task_id}/review")
async def submit_review(
    task_id: int,
    payload: ReviewTaskActionRequest,
) -> dict:
    """Submit a review decision for a review task."""
    success = await admin_service.review_task(
        task_id=task_id,
        review_result=payload.review_result,
        review_comment=payload.review_comment,
        reviewer_id=payload.reviewer_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="审核任务不存在。")
    return {
        "message": "审核结果已提交。",
        "taskId": task_id,
        "reviewResult": payload.review_result,
    }


@router.get("/admin/qa/statistics/failure-types")
async def get_failure_type_statistics() -> list[dict]:
    """Statistics: count failed questions grouped by failure type."""
    return await admin_service.statistics_failure_types()


@router.get("/admin/qa/statistics/inaccurate-types")
async def get_inaccurate_type_statistics() -> list[dict]:
    """Statistics: count inaccurate feedback grouped by question intent."""
    return await admin_service.statistics_inaccurate_types()
