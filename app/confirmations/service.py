from pydantic import BaseModel


class ConfirmationDecision(BaseModel):
    selected_option: str
    decision_comment: str | None = None


class ConfirmationService:
    def decide(self, confirmation_id: str, request: ConfirmationDecision) -> dict:
        status = "approved" if request.selected_option == "approve" else "rejected"
        return {
            "id": confirmation_id,
            "status": status,
            "selected_option": request.selected_option,
            "decision_comment": request.decision_comment,
        }
