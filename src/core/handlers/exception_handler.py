from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.validators.exceptions import DomainValidationError, EntityNotFoundException, ExternalServiceException, ForbiddenException, UnauthorizedException


# src/core/exception_handlers.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def configure_exception_handlers(application: FastAPI):
    """
    Inyecta los manejadores de excepciones estándar a cualquier aplicación FastAPI.
    """
    
    # 1. Manejador para Token Inválido / No Autenticado (401)
    @application.exception_handler(UnauthorizedException)
    async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized", "detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"} # Estándar HTTP
        )

    # 2. Manejador para Permisos Insuficientes por Rol (403)
    @application.exception_handler(ForbiddenException)
    async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden", "detail": exc.message}
        )

    # 3. Manejador para Errores de Negocio - Entidad No Encontrada (404)
    @application.exception_handler(EntityNotFoundException)
    async def entity_not_found_handler(request: Request, exc: EntityNotFoundException):
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "message": exc.message}
        )

    # 4. Manejador para Errores de Negocio - Validación (400 o 422)
    @application.exception_handler(DomainValidationError)
    async def domain_validation_handler(request: Request, exc: DomainValidationError):
        return JSONResponse(
            status_code=400, # 400 Bad Request es ideal para reglas de negocio
            content={"error": "Business Rule Violation", "message": exc.message}
        )

    # 5. Manejador para Caídas de Infraestructura Externa (502 Bad Gateway)
    @application.exception_handler(ExternalServiceException)
    async def external_service_handler(request: Request, exc: ExternalServiceException):
        # 502 Bad Gateway indica que tu servidor funciona, pero el de un tercero (Azure/Google) falló
        return JSONResponse(
            status_code=502,
            content={"error": "External Service Dependency Error", "detail": exc.message}
        )

    # 6. Manejador Global (El "Atrapalotodo" para errores de código inesperados - 500)
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # En producción, aquí deberías enviar el log a un sistema como Sentry o Datadog
        print(f"[CRÍTICO] Error no controlado: {exc}") 
        return JSONResponse(
            status_code=500,
            content={"message": "Error interno del sistema", "detail": "Contacte a soporte técnico"},
        )