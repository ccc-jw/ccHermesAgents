from pydantic import BaseModel


class ResearchReport(BaseModel):
    topic: str
    options: list[str]
    recommendation: str
    evidence: list[str]
