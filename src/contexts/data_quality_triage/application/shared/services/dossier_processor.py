import logging
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

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
        self.session = session

    async def execute(self, dni: str, batch_id: UUID, activity_type_str: str) -> TriageCase:
        # 1. Recuperar los documentos enriquecidos
        docs = await self.doc_repo.get_by_dni(dni, batch_id)
        if not docs:
            logger.warning(f"No se encontraron documentos para el DNI {dni} en el lote {batch_id}")
            raise Exception("No documents found")

        # 2. La Factory decide la estrategia basandose en el contexto
        strategy = self.strategy_factory.get_strategy(
            document_codes={doc.document_code for doc in docs if doc.document_code}, 
            activity_type_str=activity_type_str
        )
        
        from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
        activity_type = ActivityType(activity_type_str)
        
        context = {}
        if activity_type == ActivityType.EDUCA_INSCRIPTION:
            try:
                res = await self.session.execute(text("SELECT name, is_active FROM schools WHERE is_active = true"))
                schools = [{"name": row[0], "is_active": row[1]} for row in res.fetchall()]
                context["schools"] = schools
            except Exception as e:
                logger.error(f"Error fetching schools: {e}")

        # 3. Ejecutar la validacion cruzada y construir el caso
        existing_case = await self.triage_repo.get_by_dossier(batch_id, dni)
        case = strategy.execute(
            batch_id=batch_id, 
            activity_type=activity_type, 
            dni_reference=dni, 
            documents=docs,
            context=context
        )
        if existing_case:
            case.id = existing_case.id
            case.created_at = existing_case.created_at

        # --- DUPLICATE / FUZZY MATCH CHECK ---
        b_data = case.dossier_data.get("beneficiary", {})
        b_dni = b_data.get("dni", dni)
        b_first = b_data.get("first_name", "") or ""
        b_last = b_data.get("last_name", "") or ""
        
        try:
            # Check exact match
            res_exact = await self.session.execute(
                text("SELECT dni FROM persons WHERE dni = :dni"),
                {"dni": b_dni}
            )
            exact_match = res_exact.fetchone()
            
            if not exact_match and (b_first or b_last):
                # We check for a fuzzy match on name/last name in the persons table
                # For simplicity, we match if the first word of first_name AND first word of last_name match
                first_word = b_first.split()[0][:5] if b_first.split() else ""
                last_word = b_last.split()[0][:5] if b_last.split() else ""
                
                if len(first_word) >= 3 and len(last_word) >= 3:
                    res_fuzzy = await self.session.execute(
                        text("""
                            SELECT first_name, last_name, dni 
                            FROM persons 
                            WHERE type = 'beneficiary' 
                              AND first_name ILIKE :f 
                              AND last_name ILIKE :l
                            LIMIT 3
                        """),
                        {"f": f"%{first_word}%", "l": f"%{last_word}%"}
                    )
                    fuzzy_matches = res_fuzzy.fetchall()
                    if fuzzy_matches:
                        match_names = ", ".join([f"{row[0]} {row[1]} (DNI: {row[2]})" for row in fuzzy_matches])
                        suggested_dni = fuzzy_matches[0][2]
                        
                        from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
                        case.discrepancies.append(FieldDiscrepancy(
                            field_name="beneficiary.dni",
                            expected_pattern=suggested_dni,
                            actual_value=b_dni,
                            rule_description=f"Posible coincidencia encontrada en base de datos: {match_names}. Valide si es la misma persona con un DNI mal escaneado.",
                            severity="AI_INSIGHT"
                        ))
        except Exception as e:
            logger.error(f"Error in fuzzy matching: {e}", exc_info=True)

        # --- DUPLICATE ENROLLMENT CHECK ---
        try:
            res_batch = await self.session.execute(
                text("SELECT activity_id FROM document_batches WHERE id = :bid"),
                {"bid": str(batch_id)}
            )
            batch_row = res_batch.fetchone()
            if batch_row and batch_row[0]:
                activity_id_str = str(batch_row[0])
                res_enroll = await self.session.execute(
                    text("""
                        SELECT 1 FROM beneficiary_enrollments e
                        JOIN persons p ON p.id = e.beneficiary_id
                        WHERE p.dni = :dni AND e.activity_code = :act
                    """),
                    {"dni": b_dni, "act": activity_id_str}
                )
                if res_enroll.fetchone():
                    from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_verdict import TriageVerdict
                    
                    case.discrepancies.append(FieldDiscrepancy(
                        field_name="beneficiary.dni",
                        expected_pattern="DNI no inscrito en esta actividad",
                        actual_value=b_dni,
                        rule_description=f"El DNI {b_dni} ya se encuentra inscrito en esta actividad. No se pueden procesar inscripciones duplicadas.",
                        severity="ERROR",
                        document_code="DOMINIO"
                    ))
                    
                    case.status = TriageStatus.REJECTED
                    case.verdict = TriageVerdict.AUTOMATICALLY_REJECTED
        except Exception as e:
            logger.error(f"Error checking duplicate enrollment: {e}", exc_info=True)
        # -------------------------------------

        # 4. Persistencia y Eventos
        await self.triage_repo.save(case)
        await self._audit_and_dispatch(case, is_new=(existing_case is None))
        await self.session.commit()
        return case

    async def _audit_and_dispatch(self, case: TriageCase, is_new: bool = True) -> None:
        self.session.add(TriageAuditLogModel(
            id=uuid4(), triage_case_id=case.id,
            action="CREATED" if is_new else "EVALUATED", performed_by=SYSTEM_UUID,
            previous_status=None, new_status=case.status.value,
            details={
                "verdict":       case.verdict.value,
                "error_count":   sum(1 for d in case.discrepancies if d.severity == "ERROR"),
                "warning_count": sum(1 for d in case.discrepancies if d.severity == "WARNING"),
            },
        ))
        for event in case.pending_events:
            await EventDispatcher.dispatch(event)
        case.clear_events()
