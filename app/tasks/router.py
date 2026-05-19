from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.tasks.contracts import TaskStartRequest
from app.tasks.service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/{task_id}/start")
def start_task(task_id: str, request: TaskStartRequest) -> ApiResponse:
    return ApiResponse(success=True, data=TaskService().start_task(task_id, request))
