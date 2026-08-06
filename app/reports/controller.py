import io
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse

from adapters.dependencies import DatabaseSessionDep, WithPermission
from auth.service import CurrentUser
from entities.report_artifact import ReportArtifact, ReportArtifactSchema
from entities.role import Permission
from entities.task import TaskSchema

from . import service
from .models import CreateReportData

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    dependencies=[WithPermission(Permission.RunPartialRecordTasks)],
)


@router.post("/task", response_model=TaskSchema)
async def create_report(
    data: Annotated[CreateReportData, Body(...)],
    current_user: CurrentUser,
    db_session: DatabaseSessionDep,
):
    return await service.create_report(data, current_user.user_id, db_session)


@router.get("", response_model=list[ReportArtifactSchema])
def list_reports(
    db_session: DatabaseSessionDep,
    tool: str | None = None,
    task_id: str | None = None,
):
    query = db_session.query(ReportArtifact)
    if tool:
        query = query.filter(ReportArtifact.tool == tool)
    if task_id:
        try:
            query = query.filter(ReportArtifact.task_id == uuid.UUID(task_id))
        except ValueError:
            return []
    return query.order_by(ReportArtifact.created_at.desc()).all()


@router.get("/{artifact_id}/download")
def download_report(artifact_id: str, db_session: DatabaseSessionDep):
    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Report artifact not found") from exc

    artifact = ReportArtifact.find(db_session, artifact_uuid)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Report artifact not found")

    return StreamingResponse(
        io.BytesIO(artifact.blob),
        media_type=artifact.content_type,
        headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"'},
    )
