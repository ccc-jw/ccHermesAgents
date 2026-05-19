from fastapi import APIRouter

from app.escalations.service import EscalationDecision, EscalationService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


@router.post("/{escalation_id}/decision")
def decide(escalation_id: str, request: EscalationDecision) -> ApiResponse:
    return ApiResponse(success=True, data=EscalationService().decide(escalation_id, request))
