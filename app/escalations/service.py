from pydantic import BaseModel


class EscalationDecision(BaseModel):
    decision: str
    comment: str | None = None


class EscalationService:
    def decide(self, escalation_id: str, request: EscalationDecision) -> dict:
        return {"id": escalation_id, "decision": request.decision, "status": "decided"}
