from sqlalchemy.orm import Session

from entities.task import Task

from .models import SearchTasksRequest, SearchTasksResponse, TaskFilter, TaskSummary

SORT_COLUMNS = {
    "created_at": Task.created_at,
    "started_at": Task.started_at,
    "finished_at": Task.finished_at,
}


def search_tasks(request: SearchTasksRequest, db: Session) -> SearchTasksResponse:
    query = db.query(Task)
    query = _apply_filters(query, request.filters)

    total = query.count()

    sort_col = SORT_COLUMNS.get(request.sort_by, Task.created_at)
    if request.sort_order == "desc":
        sort_col = sort_col.desc()
    query = query.order_by(sort_col)

    offset = (request.page - 1) * request.page_size
    tasks = query.offset(offset).limit(request.page_size).all()

    return SearchTasksResponse(
        items=[_to_summary(t) for t in tasks],
        total=total,
        page=request.page,
        page_size=request.page_size,
    )


def _apply_filters(query, filters: TaskFilter):
    if filters.type:
        query = query.filter(Task.type.in_(filters.type))
    if filters.status:
        query = query.filter(Task.status.in_(filters.status))
    if filters.severity:
        query = query.filter(Task.severity.in_(filters.severity))
    if filters.created_by:
        query = query.filter(Task.created_by == filters.created_by)
    return query


def _to_summary(task: Task) -> TaskSummary:
    return TaskSummary(
        task_id=task.task_id,
        name=task.name,
        type=task.type.value,
        status=task.status.value,
        severity=task.severity.value,
        created_by=task.created_by,
        created_at=task.created_at,
        started_at=task.started_at,
        finished_at=task.finished_at,
        progress=task.progress,
        traceback_lines=task.traceback_lines,
    )
