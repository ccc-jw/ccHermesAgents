from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.issues.service import IssueCreate, IssueService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


@router.post("")
def create_issue(
    project_id: str, request: IssueCreate, session: Session = Depends(get_session)
) -> ApiResponse:
    return ApiResponse(success=True, data=IssueService(session).create_issue(project_id, request))
