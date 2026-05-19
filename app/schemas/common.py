from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    data: dict
    request_id: str = "req_test"
