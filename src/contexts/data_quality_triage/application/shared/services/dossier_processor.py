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
        # La sugerencia fuzzy SOLO dispara cuando el posible duplicado DIFIERE del
        # expediente en DNI y/o nombre. Si el candidato coincide en ambos (mismo
        # DNI Y mismo nombre), no es una sugerencia: es el match MDM de identidad
        # (exact_match), que la UI ya resuelve rellenando/bloqueando los campos
        # protegidos. Regla de negocio acordada:
        #   - DNI idéntico + nombre distinto   → NO (es match MDM por DNI).
        #   - DNI idéntico + nombre idéntico   → NO (misma persona, match MDM).
        #   - DNI distinto + nombre idéntico   → SÍ (OCR leyó mal el DNI) — caso
        #     ANDRE: el lote se agrupó con un DNI mal leído, el maestro confirma.
        #   - DNI distinto + nombre distinto   → SÍ (homónimo/apellidos cercanos,
        #     posible DNI mal leído).
        b_data = case.dossier_data.get("beneficiary", {})
        b_dni = b_data.get("dni", dni)
        b_first = b_data.get("first_name", "") or ""
        b_last = b_data.get("last_name", "") or ""
        
        try:
            # Check exact match (beneficiario YA registrado con ese DNI)
            res_exact = await self.session.execute(
                text("SELECT dni FROM persons WHERE dni = :dni"),
                {"dni": b_dni}
            )
            exact_match = res_exact.fetchone()
            
            if not exact_match and (b_first or b_last):
                # Sugerencia fuzzy robusta: busca candidatos por nombre/apellido
                # normalizados (sin acentos), resiste intercambios OCR de
                # columnas, nombres incompletos y devuelve los más cercanos
                # ordenados por puntaje compuesto (nombre + apellidos + DNI).
                from src.contexts.data_quality_triage.application.shared.services.beneficiary_fuzzy_matcher import BeneficiaryFuzzyMatcher
                suggestions = await BeneficiaryFuzzyMatcher(self.session).find_suggestions(
                    first_name=b_first,
                    last_name=b_last,
                    dni=b_dni,
                    limit=3,
                )

                if suggestions:
                    primary = suggestions[0]
                    primary_label = f"{primary.first_name} {primary.last_name} · DNI {primary.dni}"
                    suggested_dni = primary.dni
                    extras = suggestions[1:]
                    if extras:
                        extra_labels = ", ".join(
                            f"{c.first_name} {c.last_name} (DNI: {c.dni})" for c in extras
                        )
                        description = (
                            f"Quizá este beneficiario es → {primary_label}. "
                            f"También podría ser: {extra_labels}. Valide si es la misma "
                            f"persona con un DNI o nombre mal escaneado."
                        )
                    else:
                        description = (
                            f"Quizá este beneficiario es → {primary_label}. "
                            f"Valide si es la misma persona con un DNI o nombre mal escaneado."
                        )

                    from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
                    case.discrepancies.append(FieldDiscrepancy(
                        field_name="beneficiary.dni",
                        expected_pattern=suggested_dni,
                        actual_value=b_dni,
                        rule_description=description,
                        severity="AI_INSIGHT"
                    ))
        except Exception as e:
            logger.error(f"Error in fuzzy matching: {e}", exc_info=True)

        # --- DUPLICATE REGISTRATION CHECK ---
        # Detecta dos situaciones para el MISMO DNI y la MISMA actividad:
        #   1) Ya matriculado (beneficiary_enrollments): caso aprobado persistido.
        #   2) Expediente en trámite (triage_cases no rechazado): pendiente de
        #      revisión/corrección o aprobado sin matrícula aún.
        # En ambos casos el caso se rechaza automáticamente: no se puede registrar
        # dos veces el mismo beneficiario en una actividad.
        try:
            res_batch = await self.session.execute(
                # FIX: la tabla real es `extraction_batches` (modelo ExtractionBatchModel).
                # Antes se consultaba `document_batches` (tabla inexistente), la query
                # lanzaba excepción y el `except` la tragaba: el check NUNCA disparaba y
                # los DNI ya matriculados pasaban como duplicados.
                text("SELECT activity_id FROM extraction_batches WHERE id = :bid"),
                {"bid": str(batch_id)}
            )
            batch_row = res_batch.fetchone()
            if batch_row and batch_row[0]:
                activity_id_str = str(batch_row[0])
                duplicate_reason = None

                # 1) Matrícula existente en la actividad
                res_enroll = await self.session.execute(
                    text("""
                        SELECT 1 FROM beneficiary_enrollments e
                        JOIN persons p ON p.id = e.beneficiary_id
                        WHERE p.dni = :dni AND e.activity_code = :act
                    """),
                    {"dni": b_dni, "act": activity_id_str}
                )
                if res_enroll.fetchone():
                    duplicate_reason = f"El DNI {b_dni} ya se encuentra inscrito en esta actividad. No se pueden procesar inscripciones duplicadas."

                # 2) Expediente en trámite para el mismo DNI y actividad (se excluye
                #    el propio caso que se está procesando y los rechazados)
                if not duplicate_reason:
                    res_pending = await self.session.execute(
                        text("""
                            SELECT 1 FROM triage_cases tc
                            JOIN extraction_batches eb ON eb.id = tc.batch_id
                            WHERE eb.activity_id = :act
                              AND tc.dossier_data->'beneficiary'->>'dni' = :dni
                              AND tc.status <> 'REJECTED'
                              AND tc.id <> :current_case_id
                            LIMIT 1
                        """),
                        {"act": activity_id_str, "dni": b_dni, "current_case_id": str(case.id)}
                    )
                    if res_pending.fetchone():
                        duplicate_reason = f"El DNI {b_dni} ya tiene un expediente en trámite (pendiente de revisión o aprobación) para esta actividad. No se pueden procesar inscripciones duplicadas."

                if duplicate_reason:
                    from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
                    from src.contexts.data_quality_triage.domain.shared.value_objects.triage_verdict import TriageVerdict
                    
                    case.discrepancies.append(FieldDiscrepancy(
                        field_name="beneficiary.dni",
                        expected_pattern="DNI no inscrito en esta actividad",
                        actual_value=b_dni,
                        rule_description=duplicate_reason,
                        severity="ERROR",
                        document_code="DOMINIO"
                    ))
                    
                    case.status = TriageStatus.REJECTED
                    case.verdict = TriageVerdict.AUTOMATICALLY_REJECTED
        except Exception as e:
            logger.error(f"Error checking duplicate registration: {e}", exc_info=True)
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
