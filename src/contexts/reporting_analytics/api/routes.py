from fastapi import APIRouter

router = APIRouter(prefix="/reporting", tags=["Reporting & Analytics"])

@router.get("/health")
async def health_check():
    return {"status": "ok", "context": "Reporting & Analytics"}
