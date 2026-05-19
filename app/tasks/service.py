import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.core.time import utc_now_iso
from app.models.task import Task
from app.models.task_contract import TaskContract as TaskContractModel
from app.models.task_run import TaskRun
from app.runners.types import TaskContract
from app.tasks.contracts import TaskStartRequest


class TaskService:
    def __init__(self, session: Session):
        self.session = session

    def start_task(self, task_id: str, request: TaskStartRequest) -> dict:
        task = self.session.get(Task, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        now = utc_now_iso()
        contract = TaskContract(
            task_goal=task.title,
            role=task.owner_agent,
            phase=task.phase,
            input_artifacts=self._loads_list(task.input_artifacts_json),
            expected_artifacts=self._loads_list(task.expected_artifacts_json),
        )
        contract_row = TaskContractModel(
            id=new_id("contract"),
            task_id=task.id,
            project_id=task.project_id,
            task_goal=contract.task_goal,
            role=contract.role,
            phase=contract.phase,
            contract_json=contract.model_dump_json(),
            created_by=task.created_by,
            created_at=now,
        )
        task_run = TaskRun(
            id=new_id("run"),
            task_id=task.id,
            project_id=task.project_id,
            task_contract_id=contract_row.id,
            agent_name=task.owner_agent,
            runner_type=request.runner_type,
            workspace_strategy=request.workspace_strategy,
            created_at=now,
            updated_at=now,
        )
        task.status = "queued"
        task.runner_type = request.runner_type
        task.workspace_strategy = request.workspace_strategy
        task.updated_at = now
        self.session.add_all([contract_row, task_run])
        self.session.commit()
        return {"task_run_id": task_run.id, "status": task_run.status}

    def _loads_list(self, value: str | None) -> list[str]:
        if value is None:
            return []
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
