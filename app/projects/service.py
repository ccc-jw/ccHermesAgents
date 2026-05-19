from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.models.project import Project
from app.schemas.project import ProjectCreate


class ProjectService:
    def __init__(self, session: Session):
        self.session = session

    def create_project(self, request: ProjectCreate) -> dict:
        now = utc_now_iso()
        project = Project(
            id=new_id("proj"),
            name=request.name,
            description=request.description,
            owner_user_id=request.owner_user_id,
            repo_url=request.repo_url,
            default_branch=request.default_branch,
            workflow_template=request.workflow_template,
            size_level=request.size_level,
            created_at=now,
            updated_at=now,
        )
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "current_phase": project.current_phase,
        }
