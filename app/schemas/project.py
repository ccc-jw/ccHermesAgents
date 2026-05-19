from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    owner_user_id: str
    repo_url: str | None = None
    default_branch: str = "main"
    initial_requirement: str | None = None
    size_level: str = "M"
    workflow_template: str = "standard"
