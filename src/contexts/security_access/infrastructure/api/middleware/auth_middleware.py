# src/infrastructure/middleware/auth_middleware.py

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.contexts.security_access.domain.ports.token_provider_port import TokenProviderPort

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token_provider: TokenProviderPort):
        super().__init__(app)
        self.token_provider = token_provider
        # Lista de rutas públicas que no requieren autenticación
        self.excluded_paths = [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/openapi.json",
            "/auth/login",
            "/auth/refresh",
            "/auth/docs",
            "/auth/openapi.json",
            "/api/v1/intake/docs",
            "/api/v1/intake/openapi.json",
            "/api/v1/triage/openapi.json",
            "/api/v1/triage/docs"
        ]

    async def dispatch(self, request: Request, call_next):
        # 1. Filtro de exclusión: Pasa directo si la ruta es pública
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # 2. Extracción y validación del header Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                content={"detail": "Missing or invalid token"}
            )
        
        # Extraer el token después de 'Bearer '
        token = auth_header.split(" ")[1]

        # 3. Validación y Decodificación del token
        try:
            # Decodificamos el token usando el provider del dominio
            claims = self.token_provider.decode_internal_token(token)
            # 4. Inyección de identidad en el estado de la petición
            # Esto permite que tus endpoints accedan a request.state.user
            request.state.user = claims
            
        except Exception:
            # Retornamos un error estructurado en caso de fallo en la validación
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                content={"detail": "Invalid or expired token"}
            )

        # Si todo es correcto, permitimos que la petición continúe
        return await call_next(request)