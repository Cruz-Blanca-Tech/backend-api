from fastapi import Depends
from src.contexts.document_intake_ocr.application.use_cases.programs.create_program import CreateProgramUseCase
from src.contexts.document_intake_ocr.application.use_cases.programs.list_program import ListProgramsUseCase
from src.contexts.document_intake_ocr.application.use_cases.programs.update_program import UpdateProgramUseCase
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_program_repository import SqlProgramRepository
from src.core.database import get_async_db

# 1. Instancia base
def get_program_repository(db= Depends(get_async_db))  -> SqlProgramRepository:
    return SqlProgramRepository(db)

# 2. Casos de Uso específicos de Programas
def get_create_program_use_case(repo: SqlProgramRepository = Depends(get_program_repository)):
    return CreateProgramUseCase(repository=repo)

def get_update_program_use_case(repo: SqlProgramRepository = Depends(get_program_repository)):
    return UpdateProgramUseCase(repository=repo)

def get_list_programs_use_case(repo: SqlProgramRepository = Depends(get_program_repository)):
    return ListProgramsUseCase(repository=repo)