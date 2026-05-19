from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.time import utc_now_iso
from app.models.confirmation import Confirmation


class ConfirmationDecision(BaseModel):
    selected_option: str
    decision_comment: str | None = None


class ConfirmationService:
    def __init__(self, session: Session):
        self.session = session

    def decide(self, confirmation_id: str, request: ConfirmationDecision) -> dict:
        confirmation = self.session.get(Confirmation, confirmation_id)
        if confirmation is None:
            raise HTTPException(status_code=404, detail="Confirmation not found")

        now = utc_now_iso()
        confirmation.status = "approved" if request.selected_option == "approve" else "rejected"
        confirmation.selected_option = request.selected_option
        confirmation.decision_comment = request.decision_comment
        confirmation.decided_at = now
        confirmation.updated_at = now
        self.session.commit()
        return {
            "id": confirmation.id,
            "status": confirmation.status,
            "selected_option": confirmation.selected_option,
            "decision_comment": confirmation.decision_comment,
        }
