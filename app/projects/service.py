from app.core.ids import new_id
from app.schemas.project import ProjectCreate


class ProjectService:
    def create_project(self, request: ProjectCreate) -> dict:
        return {
            "id": new_id("proj"),
            "name": request.name,
            "status": "active",
            "current_phase": "INIT",
        }
