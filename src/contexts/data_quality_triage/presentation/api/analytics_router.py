from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_async_db
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_analytics_repository import SqlAnalyticsRepository
from src.contexts.data_quality_triage.application.shared.schemas.analytics_schemas import (
    TriageSummaryMetricsResponse, 
    TriageIssuesResponse,
    TopIssueResponse
)

router = APIRouter(
    prefix="/api/v1/triage/analytics",
    tags=["Triage Analytics"],
    responses={404: {"description": "Not found"}}
)

@router.get("/summary", response_model=TriageSummaryMetricsResponse)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Obtiene métricas agregadas del Triaje (Total procesados, estado actual, promedio de confianza OCR).
    """
    repo = SqlAnalyticsRepository(db)
    metrics = await repo.get_summary_metrics()
    return TriageSummaryMetricsResponse(**metrics)

@router.get("/issues", response_model=TriageIssuesResponse)
async def get_top_issues(
    limit: int = 5,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Obtiene el top N de discrepancias o errores más comunes detectados por el Motor de Calidad.
    """
    repo = SqlAnalyticsRepository(db)
    issues = await repo.get_top_issues(limit)
    return TriageIssuesResponse(top_issues=[TopIssueResponse(**i) for i in issues])


# src/contexts/data_quality_triage/application/shared/services/dossier_processor.py
import logging
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
# Importación de Entidades de Dominio e Interfaces (Puertos)
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.strategies.triage_strategy_factory import TriageStrategyFactory
from src.contexts.data_quality_triage.domain.shared.repositories.document_read_repository import DocumentReadRepository
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import EntityNotFoundException, DomainValidationError
logger = logging.getLogger(__name__)
SYSTEM_UUID = UUID("00000000-0000-0000-0000-000000000000")
class ProcessDossierUseCase:
    """
    Caso de Uso Principal: Orquesta la recolección de documentos OCR, la ejecución
    del motor de reglas de calidad (estrategia) y la persistencia transaccional.
    """
    
    # PATRÓN DE INYECCIÓN DE DEPENDENCIAS (Dependency Injection)
    # Recibe las implementaciones concretas en el constructor, respetando
    # el Principio de Inversión de Dependencias (SOLID: DIP).
    def __init__(
        self, 
        triage_repo: SqlTriageRepository, 
        doc_repo: DocumentReadRepository,
        strategy_factory: TriageStrategyFactory,
        session: AsyncSession
    ):
        self.triage_repo = triage_repo
        self.doc_repo = doc_repo
        self.strategy_factory = strategy_factory
        self.session = session # Manejador de Transacciones (Unit of Work)
    async def execute(self, dni: str, batch_id: UUID, activity_type_str: str) -> TriageCase:
        
        # 1. RECUPERACIÓN DE DATOS (Repository Pattern)
        # Se extraen de la base de datos todos los documentos previamente 
        # procesados por la IA de Azure para un DNI específico.
        docs = await self.doc_repo.get_by_dni(dni)
        if not docs:
            logger.warning(f"No se encontraron documentos para el DNI {dni} en el lote {batch_id}")
            raise Exception("No documents found")
        # 2. PATRÓN FÁBRICA (Factory Pattern) Y ESTRATEGIA (Strategy Pattern)
        # El sistema decide dinámicamente qué conjunto de reglas aplicar (Strategy)
        # basándose en los documentos presentados y el tipo de actividad.
        # Esto evita bloques monolíticos de "if-else" y permite alta escalabilidad.
        strategy = self.strategy_factory.get_strategy(
            document_codes={doc.document_code for doc in docs if doc.document_code}, 
            activity_type_str=activity_type_str
        )
        
        from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
        activity_type = ActivityType(activity_type_str)
        
        # 3. VALIDACIÓN CRUZADA (Ejecución del Motor de Reglas)
        # La estrategia instanciada ejecuta la validación semántica cruzada,
        # evalúa los umbrales de confianza (Confidence Scores) y genera
        # el Expediente (TriageCase) final con sus posibles discrepancias.
        case = strategy.execute(
            batch_id=batch_id, 
            activity_type=activity_type, 
            dni_reference=dni, 
            documents=docs
        )
        # 4. PERSISTENCIA Y PATRÓN OBSERVADOR (Event-Driven)
        # Se guarda el expediente y se despachan los eventos asincrónicos
        # dentro del alcance de una única transacción ACID de base de datos.
        await self.triage_repo.save(case)
        await self._audit_and_dispatch(case)
        
        await self.session.commit() # Unit of Work: Commit
        return case
    async def _audit_and_dispatch(self, case: TriageCase) -> None:
        """
        Método interno para garantizar el Event Sourcing parcial (Audit Log)
        y disparar eventos de dominio a otros contextos del sistema.
        """
        # Creación inmutable de la pista de auditoría en Base de Datos
        self.session.add(TriageAuditLogModel(
            id=uuid4(), triage_case_id=case.id,
            action="CREATED", performed_by=SYSTEM_UUID,
            previous_status=None, new_status=case.status.value,
            details={
                "verdict":       case.verdict.value,
                "error_count":   sum(1 for d in case.discrepancies if d.severity == "ERROR"),
                "warning_count": sum(1 for d in case.discrepancies if d.severity == "WARNING"),
            },
        ))
        
        # Publicación en el Bus de Eventos (EventDispatcher)
        for event in case.pending_events:
            await EventDispatcher.dispatch(event)
        
        case.clear_events()