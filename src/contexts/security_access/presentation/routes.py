from fastapi import FastAPI, Depends, Request
from fastapi.openapi.utils import get_openapi

from src.contexts.security_access.domain.value_objects.role import Role
from src.contexts.security_access.domain.value_objects.token_claims import TokenClaims
from src.contexts.security_access.infrastructure.api.dependencies.role_checker import RoleChecker
from src.contexts.security_access.presentation.api.auth_router import router as auth_router_instance
from src.contexts.security_access.presentation.api.user_router import router as user_router_instance
from src.contexts.security_access.presentation.dto.login_response import UserResponse

# 1. Creamos la instancia de FastAPI para el Bounded Context de Seguridad
security_app = FastAPI(
    title="Security & Access Context",
    description="API para la gestión de identidad, autenticación SSO y control de accesos (RBAC)",
    version="1.0.0"
)

# 2. Habilitamos el botón "Authorize" en el Swagger de esta sub-app
def custom_openapi():
    if security_app.openapi_schema:
        return security_app.openapi_schema
    openapi_schema = get_openapi(
        title=security_app.title,
        version=security_app.version,
        description=security_app.description,
        routes=security_app.routes,
    )
    # Configuración del esquema JWT Bearer
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer Auth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    # Forzamos a que todas las rutas usen este esquema por defecto
    openapi_schema["security"] = [{"Bearer Auth": []}]
    security_app.openapi_schema = openapi_schema
    return security_app.openapi_schema

security_app.openapi = custom_openapi

@security_app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "context": "Security & Access"}

# 3. Incluimos los routers internos del contexto
security_app.include_router(auth_router_instance, tags=["Authentication"])
security_app.include_router(user_router_instance, tags=["Users"])
