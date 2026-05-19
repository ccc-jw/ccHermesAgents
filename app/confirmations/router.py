from fastapi import APIRouter

from app.confirmations.service import ConfirmationDecision, ConfirmationService
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/confirmations", tags=["confirmations"])


@router.post("/{confirmation_id}/decide")
def decide(confirmation_id: str, request: ConfirmationDecision) -> ApiResponse:
    return ApiResponse(success=True, data=ConfirmationService().decide(confirmation_id, request))
