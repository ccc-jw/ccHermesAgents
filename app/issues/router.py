from fastapi import APIRouter

from app.issues.service import IssueCreate, IssueService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/projects/{project_id}/issues", tags=["issues"])


@router.post("")
def create_issue(project_id: str, request: IssueCreate) -> ApiResponse:
    return ApiResponse(success=True, data=IssueService().create_issue(project_id, request))
