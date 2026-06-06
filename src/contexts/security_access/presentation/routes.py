from fastapi import APIRouter

from src.contexts.security_access.presentation.api.auth_router import router as auth_router_instance

router = APIRouter(prefix="/security", tags=["Security & Access"])

router.include_router(auth_router_instance)

@router.get("/health")
async def health_check():
    return {"status": "ok", "context": "Security & Access"}

@router.get("/me")
async def get_me():
    # Por ahora es un mock, más adelante aquí usarás 
    # verify_google_token como dependencia
    return {
        "user": "operativo@cruzblanca.org",
        "role": "operativo",
        "context": "Security & Access"
    }