from fastapi import APIRouter

from app.projects.service import ProjectService
from app.schemas.common import ApiResponse
from app.schemas.project import ProjectCreate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
def create_project(request: ProjectCreate) -> ApiResponse:
    return ApiResponse(success=True, data=ProjectService().create_project(request))
