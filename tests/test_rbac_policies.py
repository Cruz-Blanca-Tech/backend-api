"""RF-02 / RF-27: matriz de control de acceso por rol de toda la API.

Recorre las rutas de cada contexto montado en `src.main.app` y verifica qué roles
exige cada una. Si alguien agrega un endpoint sin la política correcta, esta
prueba falla. Además comprueba, con peticiones reales firmadas, que un rol sin
permiso recibe 403 antes de tocar la base de datos.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.core.config import settings
from src.main import app
from src.contexts.security_access.domain.value_objects.role import Role
from src.contexts.security_access.infrastructure.api.dependencies.role_checker import RoleChecker

ANY = {Role.ADMIN, Role.OPERATIVO, Role.REVISOR, Role.VISUALIZADOR}
OPS = {Role.ADMIN, Role.OPERATIVO, Role.REVISOR}
ADMIN_OP = {Role.ADMIN, Role.OPERATIVO}
ADMIN = {Role.ADMIN}


def _sub_app(mount_path: str):
    for route in app.routes:
        if getattr(route, "path", None) == mount_path:
            return route.app
    raise AssertionError(f"No se encontró la sub-aplicación montada en {mount_path}")


def _required_roles(route: APIRoute):
    """Conjunto de roles exigido por los RoleChecker de la ruta (None si no hay)."""
    checkers = []

    def walk(dependant):
        for dep in dependant.dependencies:
            if isinstance(dep.call, RoleChecker):
                checkers.append(set(dep.call.allowed_roles))
            walk(dep)

    walk(route.dependant)
    if not checkers:
        return None
    roles = set.intersection(*checkers)
    return roles


def _routes(mount_path: str):
    return [r for r in _sub_app(mount_path).routes if isinstance(r, APIRoute) and not r.path.endswith("/health")]


def _assert(mount_path, predicate, expected):
    matched = [r for r in _routes(mount_path) if predicate(r)]
    assert matched, f"Ninguna ruta coincide en {mount_path}"
    for r in matched:
        assert _required_roles(r) == expected, f"{sorted(r.methods)} {mount_path}{r.path} exige {_required_roles(r)}, se esperaba {expected}"


def test_triaje_solo_roles_de_operacion():
    _assert("/api/v1/triage", lambda r: True, OPS)


def test_carga_de_datos_solo_roles_de_operacion():
    _assert("/api/v1/intake", lambda r: r.path.startswith(("/api/v1/batches", "/api/v1/sync-extract")), OPS)


def test_catalogos_de_configuracion_solo_admin_para_escribir():
    _assert("/api/v1/intake", lambda r: r.path.startswith("/activities") and r.methods & {"POST", "PATCH"}, ADMIN)


def test_listado_de_beneficiarios_para_todo_el_personal():
    _assert("/api/v1/mdm", lambda r: r.path == "/beneficiaries" and "GET" in r.methods, ANY)


def test_ficha_y_edicion_de_beneficiarios_solo_operacion():
    _assert(
        "/api/v1/mdm",
        lambda r: r.path.startswith("/beneficiaries") and not (r.path == "/beneficiaries" and "GET" in r.methods),
        OPS,
    )


def test_colegios_lectura_todos_escritura_admin_u_operativo():
    _assert("/api/v1/mdm", lambda r: r.path.startswith("/schools") and "GET" in r.methods, ANY)
    _assert("/api/v1/mdm", lambda r: r.path.startswith("/schools") and r.methods & {"POST", "PATCH"}, ADMIN_OP)


def test_usuarios_lista_admin_u_operativo_y_cambio_de_rol_solo_admin():
    _assert("/auth", lambda r: r.path in ("/users", "/users/") and "GET" in r.methods, ADMIN_OP)
    _assert("/auth", lambda r: r.path == "/users/{user_id}/role", ADMIN)


def test_reportes_exportaciones_solo_operacion_dashboards_todos():
    _assert("/api/v1/reporting", lambda r: "/exports" in r.path, OPS)
    _assert("/api/v1/reporting", lambda r: "/exports" not in r.path, ANY)


# --- Pruebas funcionales: el rol sin permiso recibe 403 -------------------------

def _token(role: Role) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(uuid4()),
        "email": "prueba@cruz-blanca.org",
        "role": role.value,
        "name": "Usuario de prueba",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


client = TestClient(app)


@pytest.mark.parametrize("role", [Role.VISUALIZADOR, Role.OPERATIVO, Role.REVISOR])
def test_solo_admin_puede_cambiar_roles(role):
    res = client.patch(
        f"/auth/users/{uuid4()}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {_token(role)}"},
    )
    assert res.status_code == 403


def test_visualizador_no_accede_al_triaje():
    res = client.get(f"/api/v1/triage/batch/{uuid4()}/summary", headers={"Authorization": f"Bearer {_token(Role.VISUALIZADOR)}"})
    assert res.status_code == 403


def test_visualizador_no_abre_la_ficha_completa_de_un_beneficiario():
    res = client.get(f"/api/v1/mdm/beneficiaries/{uuid4()}", headers={"Authorization": f"Bearer {_token(Role.VISUALIZADOR)}"})
    assert res.status_code == 403


def test_sin_token_la_api_responde_401():
    assert client.get("/api/v1/mdm/beneficiaries").status_code == 401
