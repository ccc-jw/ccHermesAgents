from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.models.issue import Issue


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
    def __init__(self, session: Session):
        self.session = session

    def create_issue(self, project_id: str, request: IssueCreate) -> dict:
        now = utc_now_iso()
        issue = Issue(
            id=new_id("issue"),
            project_id=project_id,
            source=request.source,
            phase=request.phase,
            title=request.title,
            description=request.description,
            severity=request.severity,
            priority=request.priority,
            assigned_agent=request.assigned_agent,
            created_at=now,
            updated_at=now,
        )
        self.session.add(issue)
        self.session.commit()
        return {"id": issue.id, "project_id": issue.project_id, "title": issue.title, "status": issue.status}
