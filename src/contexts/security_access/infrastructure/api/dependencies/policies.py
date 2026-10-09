"""Políticas RBAC centralizadas (RF-02).

Espejan la matriz de acceso del frontend (cruz-blanca-app/src/config/routes.ts):
  - Todo el personal autenticado: dashboard, beneficiarios (listado enmascarado) y reportes agregados.
  - Operación (Admin, Operativo, Revisor): carga de datos, triaje, ficha completa del
    beneficiario, exportaciones con datos personales.
  - Admin u Operativo: gestión de usuarios (lectura) y colegios.
  - Solo Admin: cambio de roles, programas, actividades y catálogo documental.
"""
from src.contexts.security_access.domain.value_objects.role import Role
from src.contexts.security_access.infrastructure.api.dependencies.role_checker import RoleChecker


ALLOW_ANY_STAFF = RoleChecker([Role.ADMIN, Role.OPERATIVO, Role.REVISOR, Role.VISUALIZADOR])
ALLOW_OPERATIONS = RoleChecker([Role.ADMIN, Role.OPERATIVO, Role.REVISOR])
ALLOW_ADMIN_OR_OPERATIVO = RoleChecker([Role.ADMIN, Role.OPERATIVO])
ALLOW_ADMIN_OR_REVIEWER = RoleChecker([Role.ADMIN, Role.REVISOR])
ALLOW_ADMIN_ONLY = RoleChecker([Role.ADMIN])
