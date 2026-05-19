from pydantic import BaseModel, Field

from app.core.ids import new_id


class IssueCreate(BaseModel):
    source: str
    phase: str
    title: str
    description: str | None = None
    severity: str = "major"
    priority: str = "normal"
    assigned_agent: str | None = None
    related_artifacts: list[str] = Field(default_factory=list)
    source_task_run_id: str | None = None


class IssueService:
    def create_issue(self, project_id: str, request: IssueCreate) -> dict:
        return {"id": new_id("issue"), "project_id": project_id, "title": request.title, "status": "open"}
