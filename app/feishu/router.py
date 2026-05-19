from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/feishu", tags=["feishu"])


@router.post("/events")
async def receive_events(request: Request) -> dict:
    payload = await request.json()
    if payload.get("type") == "url_verification":
        return {"challenge": payload["challenge"]}
    return {"success": True}
