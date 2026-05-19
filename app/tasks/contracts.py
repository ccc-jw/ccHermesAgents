from pydantic import BaseModel


class TaskStartRequest(BaseModel):
    runner_type: str
    workspace_strategy: str
