from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.confirmations.service import ConfirmationDecision, ConfirmationService
from app.core.db import get_session
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/api/confirmations", tags=["confirmations"])


@router.post("/{confirmation_id}/decide")
def decide(
    confirmation_id: str, request: ConfirmationDecision, session: Session = Depends(get_session)
) -> ApiResponse:
    return ApiResponse(success=True, data=ConfirmationService(session).decide(confirmation_id, request))
