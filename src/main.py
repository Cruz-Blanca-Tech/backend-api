from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from src.contexts.security_access.infrastructure.api.middleware.auth_middleware import AuthMiddleware
from src.contexts.security_access.infrastructure.di.auth_container import AuthContainer
from src.core.config import settings
from src.contexts.security_access.presentation.routes import router as security_router
from src.contexts.document_intake_ocr.api.routes import router as intake_router
from src.contexts.data_quality_triage.api.routes import router as triage_router
from src.contexts.reporting_analytics.api.routes import router as reporting_router
from fastapi.openapi.utils import get_openapi

# Aquí tendrías tu instancia de provider (o contenedor)
# 1. Instancias la app
security = HTTPBearer()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)
auth_container = AuthContainer()
app.add_middleware(AuthMiddleware, token_provider=auth_container.token_provider)


# 2. Registras AuthMiddleware primero (se ejecutará al final, lo cual es correcto)

# 3. Registras CORSMiddleware después (se ejecutará primero, manejando el tráfico CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL,"http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    openapi_schema["security"] = [{"Bearer Auth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Aquí es buena práctica loguear el error real para ti (el desarrollador)
    print(f"Error detectado: {exc}") 
    return JSONResponse(
        status_code=500,
        content={"message": "Error interno del sistema", "detail": "Contacte a soporte"},
    )


# Registrar routers de cada Bounded Context bajo el prefijo común
app.include_router(security_router, prefix=settings.API_V1_STR)
app.include_router(intake_router, prefix=settings.API_V1_STR)
app.include_router(triage_router, prefix=settings.API_V1_STR)
app.include_router(reporting_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["General"])
async def root():
    return {
        "message": f"Bienvenido a la API de {settings.PROJECT_NAME}",
        "docs": "/docs",
        "status": "active",
    }
