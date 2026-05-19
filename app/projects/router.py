from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.projects.service import ProjectService
from app.schemas.common import ApiResponse
from app.schemas.project import ProjectCreate

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
def create_project(request: ProjectCreate, session: Session = Depends(get_session)) -> ApiResponse:
    return ApiResponse(success=True, data=ProjectService(session).create_project(request))
