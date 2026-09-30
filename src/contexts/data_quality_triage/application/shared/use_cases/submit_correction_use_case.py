import logging
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel
from src.core.events.event_dispatcher import EventDispatcher
from src.core.validators.exceptions import ConflictException, EntityNotFoundException
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy

from src.contexts.data_quality_triage.domain.shared.rules.dossier_status_validator import DossierStatusValidator
from src.contexts.data_quality_triage.domain.shared.ports.batch_status_validator import BatchStatusValidatorPort
from src.contexts.data_quality_triage.application.shared.use_cases.finalize_batch_if_complete_use_case import (
    FinalizeBatchIfCompleteUseCase,
)
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository

logger = logging.getLogger(__name__)

# Razones de rechazo estándar
REJECT_DUPLICATE_ENROLLMENT = "DUPLICATE_ENROLLMENT"

class SubmitCorrectionUseCase:
    def __init__(
        self,
        triage_repo: SqlTriageRepository,
        session: AsyncSession,
        beneficiary_repo: SqlBeneficiaryRepository,
        status_validator: Optional[DossierStatusValidator] = None,
        batch_status_validator: Optional[BatchStatusValidatorPort] = None
    ):
        self.triage_repo = triage_repo
        self.session = session
        self.beneficiary_repo = beneficiary_repo
        if status_validator:
            self.status_validator = status_validator
        elif batch_status_validator:
            self.status_validator = DossierStatusValidator(batch_status_validator=batch_status_validator)
        else:
            self.status_validator = DossierStatusValidator()

    async def execute(self, case_id: UUID, user_id: UUID, corrected_data: Dict[str, Any]) -> TriageCase:
        case = await self.triage_repo.get_by_id(case_id)
        if not case:
            raise EntityNotFoundException(f"No se encontró el caso de triaje con ID: {case_id}")
            
        await self.status_validator.validate_can_be_corrected(case)

        previous_status = case.status.value
        # El dossier del triaje persiste el género en forma F/M (el select del
        # formulario solo ofrece F/M). El maestro MDM serializa el enum
        # (MALE/FEMALE) y puede llegar hasta aquí vía el payload corregido: se
        # normaliza antes de persistir para no contaminar el dossier_data ni
        # volver a disparar GenderCoherenceRule en el siguiente reproceso.
        corrected_data = self._normalize_gender(corrected_data)
        # Red de seguridad del snapshot: si el caso no tiene original (p. ej.
        # creado antes del rollout), capturamos el dossier_data actual como
        # "primer JSON" justo antes de la primera corrección humana.
        if case.original_dossier_data is None and isinstance(case.dossier_data, dict):
            case.original_dossier_data = dict(case.dossier_data)
        case.submit_correction(corrected_data, user_id)

        # 1. Reconstituir entidad de dominio
        domain_entity = None
        is_complete = False
        domain_issues = []
        dni = None
        try:
            activity_type = ActivityType(case.activity_type)
            domain_entity = DossierFactory.reconstitute(case.dossier_data, activity_type)
            is_complete, domain_issues = domain_entity.validate_completeness()
            dni = domain_entity.beneficiary.dni
        except Exception as e:
            logger.error(f"Error reconstituting domain entity for correction validation: {str(e)}")
            is_complete = False
            domain_issues = [
                FieldDiscrepancy(
                    field_name="payload", expected_pattern="Formato válido", actual_value="Error",
                    rule_description=f"Error al parsear el payload: {str(e)}", severity="ERROR", document_code="GLOBAL"
                )
            ]
            dni = None

        # 2. Validar documentos obligatorios
        missing_doc_discrepancies = []
        if case.activity_type == "EDUCA_INSCRIPTION":
            required_doc_map = {
                "FINS": "Ficha de Inscripción",
                "DJ": "Declaración Jurada",
                "DNIBE": "DNI del Beneficiario",
                "DNIAP": "DNI del Apoderado",
            }
            present_doc_codes = set(case.document_ids.keys()) if case.document_ids else set()
            for code, name in required_doc_map.items():
                if code not in present_doc_codes:
                    missing_doc_discrepancies.append(FieldDiscrepancy(
                        field_name=f"documents.{code}",
                        expected_pattern=f"Documento {name} ({code}) adjunto",
                        actual_value="Faltante",
                        rule_description=f"Falta el documento obligatorio: {name} ({code}). Debe adjuntar el documento para continuar.",
                        severity="ERROR",
                        document_code=code
                    ))

        # 3. CHECK DUPLICADO: solo si es EDUCA_INSCRIPTION, está completo y no faltan docs
        if (is_complete and not missing_doc_discrepancies 
                and case.activity_type == "EDUCA_INSCRIPTION" and dni):
            activity_id = await self._resolve_activity_id(case.batch_id)
            existing = await self.beneficiary_repo.get_by_dni(dni)
            if existing and any(e.activity_code == activity_id for e in existing.enrollments):
                reject_detail = (
                    f"El beneficiario {existing.first_name} {existing.last_name} "
                    f"(DNI {dni}) ya está inscrito en esta actividad (MDM id: {existing.id}). "
                    "Para modificar sus datos, use la pantalla de Beneficiarios."
                )
                case.reject(user_id, REJECT_DUPLICATE_ENROLLMENT)
                # Agregamos el detalle en discrepancies para que la UI lo muestre
                case.update_discrepancies([
                    FieldDiscrepancy(
                        field_name="beneficiary.dni",
                        expected_pattern="DNI no inscrito en esta actividad",
                        actual_value=dni,
                        rule_description=reject_detail,
                        severity="ERROR",
                        document_code="DOMINIO"
                    )
                ])
                self._add_audit_log(case_id, "REJECTED", user_id, previous_status, TriageStatus.REJECTED.value, {
                    "reject_reason": REJECT_DUPLICATE_ENROLLMENT,
                    "reject_detail": reject_detail,
                    "existing_beneficiary_id": str(existing.id)
                })
                await self.triage_repo.save(case)
                await self._maybe_finalize_batch(case.batch_id)
                await self.session.commit()
                return case

        # 4. Flujo normal según completitud
        if missing_doc_discrepancies:
            all_issues = missing_doc_discrepancies + domain_issues
            case.update_discrepancies(all_issues)
            case.status = TriageStatus.INCOMPLETE
            self._add_audit_log(case_id, "CORRECTED", user_id, previous_status, case.status.value, {
                "corrected_fields": corrected_data, 
                "missing_documents": [d.document_code for d in missing_doc_discrepancies]
            })
        elif is_complete:
            case.approve(user_id)
            case.update_discrepancies([i for i in domain_issues if i.severity != "ERROR"])
            self._add_audit_log(case_id, "CORRECTED", user_id, previous_status, TriageStatus.CORRECTED.value, {
                "corrected_fields": corrected_data
            })
            self._add_audit_log(case_id, "AUTO_APPROVED", user_id, TriageStatus.CORRECTED.value, case.status.value, {
                "verdict": case.verdict.value, "reason": "Validación manual exitosa"
            })
        else:
            case.update_discrepancies(domain_issues)
            case.status = TriageStatus.PENDING_REVIEW
            self._add_audit_log(case_id, "CORRECTED", user_id, previous_status, case.status.value, {
                "corrected_fields": corrected_data, "remaining_errors": len(domain_issues)
            })

        await self.triage_repo.save(case)
        # Commit antes de despachar, por el mismo motivo que en `dossier_processor`:
        # el handler de MDM marca `sync_status = "SYNCED"` desde su propia sesión, y
        # el `merge()` de `save()` deja la fila sucia en el identity map. Un commit
        # posterior reescribiría el `sync_status` a PENDING y se perdería el SYNCED.
        await self.session.commit()
        for event in case.pending_events:
            await EventDispatcher.dispatch(event)
        case.clear_events()

        # El lote se cierra solo si este expediente fue el último en decidirse.
        # Va DESPUÉS del despacho a propósito: recién ahí el handler de MDM dejó
        # `sync_status` en SYNCED o en FAILED, y de eso depende si el lote queda
        # FINALIZED o SYNC_FAILED. Consultarlo antes miraría un PENDING viejo y
        # cerraría el lote como si todo estuviera cargado.
        await self._maybe_finalize_batch(case.batch_id)
        await self.session.commit()
        
        return case

    async def _resolve_activity_id(self, batch_id: UUID) -> str:
        """Devuelve el `activity_id` del lote, que es lo que se guarda en
        `beneficiary_enrollments.activity_code`.

        Antes este chequeo comparaba contra el literal `"EDUCA"`, pero la columna
        guarda el UUID de la actividad (mismo valor que `extraction_batches.activity_id`).
        La comparación no podía coincidir nunca, así que el rechazo por inscripción
        duplicada no se disparaba al aprobar a mano: solo funcionaba en el
        reprocesado (`dossier_processor`), que sí usa el UUID.
        """
        from sqlalchemy import text

        result = await self.session.execute(
            text("SELECT activity_id FROM extraction_batches WHERE id = :bid"),
            {"bid": str(batch_id)},
        )
        row = result.fetchone()
        if row and row[0]:
            return str(row[0])
        # Sin lote no se puede determinar la actividad: no se rechaza nada, porque
        # inventar un id haría matchear cualquier Beneficiario con cualquier otra.
        logger.warning(
            "No se pudo resolver la actividad del lote %s; se omite el chequeo de duplicado.",
            batch_id,
        )
        return ""

    async def _maybe_finalize_batch(self, batch_id: UUID) -> None:
        """Cierra el lote si con este expediente ya quedaron todos decididos."""
        await FinalizeBatchIfCompleteUseCase(
            session=self.session, triage_repo=self.triage_repo
        ).execute(batch_id)

    def _add_audit_log(self, case_id: UUID, action: str, performed_by: UUID, previous_status: str, new_status: str, details: dict = None) -> None:
        audit_log = TriageAuditLogModel(id=uuid4(), triage_case_id=case_id, action=action, performed_by=performed_by, previous_status=previous_status, new_status=new_status, details=details)
        self.session.add(audit_log)

    @staticmethod
    def _normalize_gender(corrected_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza `beneficiary.gender` del dossier a `M`/`F` si llegó el enum
        del maestro (`MALE`/`FEMALE`). `M`/`F` ya son válidos y se conservan;
        sin género o valores no reconocidos se dejan tal cual para que el panel
        los marque como pendiente/error si aplica."""
        if not isinstance(corrected_data, dict):
            return corrected_data
        beneficiary = corrected_data.get("beneficiary")
        if not isinstance(beneficiary, dict):
            return corrected_data
        gender = beneficiary.get("gender")
        if not isinstance(gender, str):
            return corrected_data
        normalized = gender.strip().upper()
        if normalized in ("MALE", "FEMALE"):
            beneficiary["gender"] = "M" if normalized == "MALE" else "F"
        return corrected_data