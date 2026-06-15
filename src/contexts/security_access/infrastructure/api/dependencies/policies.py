

from src.contexts.security_access.domain.value_objects.role import Role
from src.contexts.security_access.infrastructure.api.dependencies.role_checker import RoleChecker


ALLOW_ADMIN_OR_REVIEWER = RoleChecker([Role.ADMIN, Role.REVISOR])
ALLOW_ANY_STAFF = RoleChecker([Role.ADMIN, Role.OPERATIVO, Role.REVISOR, Role.VISUALIZADOR])
ALLOW_ADMIN_ONLY = RoleChecker([Role.ADMIN])
