from app.core.ids import new_id
from app.tasks.contracts import TaskStartRequest


class TaskService:
    def start_task(self, task_id: str, request: TaskStartRequest) -> dict:
        return {"task_run_id": new_id("run"), "status": "CREATED"}
