# src/contexts/security_access/presentation/api/auth_router.py

from fastapi import APIRouter, Depends, Request, Response, Cookie, HTTPException, status
from pydantic import BaseModel

from src.contexts.security_access.application.services.auth_service import AuthService
# Asumimos que tienes un archivo donde inyectas las dependencias (el repositorio, el proveedor, etc.)
from src.contexts.security_access.infrastructure.dependencies import get_auth_service
from src.contexts.security_access.presentation.dto.google_login_request import GoogleLoginRequest

router = APIRouter()

@router.post("/login", summary="Iniciar sesión mediante Google SSO")
async def login(
    request: GoogleLoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        # 1. Llamamos a nuestro Application Service
        token_pair = await auth_service.authenticate_user(request.google_token)
        
        # 2. Inyectamos el Refresh Token en una Cookie Segura
        response.set_cookie(
            key="refresh_token",
            value=token_pair.refresh_token,
            httponly=True,   # El JavaScript del frontend no puede leerla (Previene XSS)
            secure=True,     # Solo viaja por HTTPS (Obligatorio en producción)
            samesite="lax",  # Mitiga ataques CSRF
            max_age=14 * 24 * 60 * 60  # La cookie dura 14 días en el navegador
        )
        
        # 3. Retornamos solo el Access Token en el body
        return {
            "access_token": token_pair.access_token,
            "token_type": "bearer"
        }
        
    except PermissionError as e:
        # Capturamos rechazos (ej. el correo no pertenece al dominio autorizado)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Token de Google inválido o malformado."
        )


@router.post("/refresh", summary="Refrescar sesión (Rotación de Tokens)")
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None),  # FastAPI extrae la cookie automáticamente
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Renueva el Access Token utilizando el Refresh Token almacenado en las cookies.
    Aplica rotación: quema el viejo y entrega uno nuevo.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="No se encontró una sesión activa. Por favor, inicie sesión nuevamente."
        )

    try:
        # 1. El servicio lee, quema, valida los 14 días y emite el nuevo par
        new_token_pair = await auth_service.refresh_user_session(refresh_token)

        # 2. Sobreescribimos la cookie con el NUEVO refresh token
        response.set_cookie(
            key="refresh_token",
            value=new_token_pair.refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=14 * 24 * 60 * 60
        )

        # 3. Entregamos el nuevo Access Token
        return {
            "access_token": new_token_pair.access_token,
            "token_type": "bearer"
        }

    except PermissionError as e:
        # Si el token fue quemado previamente, si caducaron los 14 días, o es inválido:
        # Borramos la cookie del navegador inmediatamente por seguridad
        response.delete_cookie("refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    
async def get_refresh_token(request: Request):
    # 1. Extraer la cookie por su nombre
    refresh_token = request.cookies.get("refresh_token")
    print(f"Cookies recibidas: {request.cookies}")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No se encontró la cookie de sesión")
    
    return refresh_token


# src/contexts/security_access/presentation/api/auth_router.py

@router.post("/logout")
async def logout(
    response: Response, 
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    # 1. Obtenemos el token de la cookie
    refresh_token = request.cookies.get("refresh_token")
    
    if refresh_token:
        # 2. Invalidamos en el backend (BD)
        await auth_service.logout_user(refresh_token)
    
    # 3. Borramos la cookie del navegador
    response.delete_cookie(
        key="refresh_token",
        path="/",
        domain=None # Asegúrate de que coincida con donde la creaste
    )
    
    
    return {"message": "Sesión cerrada correctamente"}