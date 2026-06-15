from fastapi import Depends

# 1. Infraestructura (Repositorio)

# 2. Aplicación (Casos de Uso)
from asd import get_async_db
from src.contexts.document_intake_ocr.application.use_cases.activities.create_activity import CreateActivityUseCase
from src.contexts.document_intake_ocr.application.use_cases.activities.get_activity_by_id import GetActivityByIdUseCase
from src.contexts.document_intake_ocr.application.use_cases.activities.update_activity import UpdateActivityUseCase
from src.contexts.document_intake_ocr.application.use_cases.activities.list_activities import ListActivitiesUseCase
from src.contexts.document_intake_ocr.domain.services.activity_validator import ActivityValidator
from src.contexts.document_intake_ocr.infrastructure.dependencies.document_catalog_deps import get_document_catalog_repository
from src.contexts.document_intake_ocr.infrastructure.dependencies.program_deps import get_program_repository
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository import SqlActivityRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_catalog_repository import SqlDocumentCatalogRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_program_repository import SqlProgramRepository

# --- PROVEEDOR BASE ---
def get_activity_repository(db= Depends(get_async_db)) -> SqlActivityRepository:
    """
    Instancia el repositorio de Actividades. 
    En el futuro, aquí se inyectará la conexión a la base de datos (Session).
    """
    return SqlActivityRepository(db)

def get_activity_validator(
    prog_repo: SqlProgramRepository = Depends(get_program_repository),
    cat_repo: SqlDocumentCatalogRepository = Depends(get_document_catalog_repository)
) -> ActivityValidator:
    return ActivityValidator(program_repo=prog_repo, catalog_repo=cat_repo)

# --- PROVEEDORES DE CASOS DE USO ---
def get_create_activity_use_case(
    act_repo: SqlActivityRepository = Depends(get_activity_repository),
    validator: ActivityValidator = Depends(get_activity_validator) # <-- Inyectamos el validador
) -> CreateActivityUseCase:
    return CreateActivityUseCase(activity_repo=act_repo, validator=validator)

def get_update_activity_use_case(
    act_repo: SqlActivityRepository = Depends(get_activity_repository),
    validator: ActivityValidator = Depends(get_activity_validator) # <-- También aquí!
) -> UpdateActivityUseCase:
    # Recuerda actualizar tu constructor del UseCase para recibir el validator
    return UpdateActivityUseCase(activity_repo=act_repo, validator=validator)

def get_by_activity_id_use_case(
    repo: SqlActivityRepository = Depends(get_activity_repository)
) -> GetActivityByIdUseCase:
    return GetActivityByIdUseCase(repository=repo)

def get_list_activities_use_case(
    repo: SqlActivityRepository = Depends(get_activity_repository)
) -> ListActivitiesUseCase:
    return ListActivitiesUseCase(repository=repo)
