from fastapi import APIRouter

router = APIRouter(prefix="/security", tags=["Security & Access"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "context": "Security & Access"}
