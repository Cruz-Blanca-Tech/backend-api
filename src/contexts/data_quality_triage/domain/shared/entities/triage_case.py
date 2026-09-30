import copy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

# Evento COMPARTIDO entre contextos (src/contexts/shared/events). Es un dataclass
# congelado, puro contrato de mensaje: no trae comportamiento ni dependencias de
# otros dominios, asi que no rompe la frontera del dominio. Lo que si evita este
# import es que la entidad tenga que conocer el bus de eventos: registra el
# hecho en `_pending_events` y la capa de aplicacion decide despacharlo.
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent

from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict

# Actor sintético para aprobaciones touchless, que no tienen usuario humano.
# Mismo sentinel que ya usa `verify_batch_completion_use_case` al publicar el
# evento a mano: `DossierApprovedEvent.approved_by` es obligatorio (UUID) y en
# touchless no hay nadie que lo llene.
SYSTEM_ACTOR_UUID = UUID("00000000-0000-0000-0000-000000000001")

class TriageCase:
    def __init__(
        self,
        id: UUID,
        batch_id: UUID,
        activity_type: str,
        dni_reference: str,
        dossier_data: Dict[str, Any],
        document_ids: Dict[str, UUID],
        confidence_scores: Dict[str, float],
        status: TriageStatus,
        verdict: TriageVerdict,
        discrepancies: List[FieldDiscrepancy],
        original_dossier_data: Optional[Dict[str, Any]] = None,
        rejection_reason: Optional[str] = None,
        resolved_by: Optional[UUID] = None,
        resolved_at: Optional[datetime] = None,
        sync_status: Optional[str] = "PENDING",
        sync_error: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ):
        self.id = id
        self.batch_id = batch_id
        self.activity_type = activity_type
        self.dni_reference = dni_reference
        self.dossier_data = dossier_data
        # Snapshot del primer JSON del expediente (post-LLM, sin intervención
        # humana). Nunca se sobrescribe: dossier_data es la data final que el
        # usuario puede corregir, original_dossier_data es la "foto" del backend.
        self.original_dossier_data = original_dossier_data
        self.document_ids = document_ids
        self.confidence_scores = confidence_scores
        self.status = status
        self.verdict = verdict
        self.discrepancies = list(discrepancies)
        self.rejection_reason = rejection_reason
        self.sync_status = sync_status or "PENDING"
        self.sync_error = sync_error
        self.resolved_by = resolved_by
        self.resolved_at = resolved_at
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = updated_at or datetime.now(timezone.utc)
        self.completed_at = completed_at
        self._pending_events: List[Any] = []

    def mark_sync_success(self) -> None:
        self.sync_status = "SYNCED"
        self.sync_error = None
        self.updated_at = datetime.now(timezone.utc)

    def mark_sync_failure(self, error_message: str) -> None:
        self.sync_status = "FAILED"
        self.sync_error = error_message
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def create_from_quality_result(
        cls,
        batch_id: UUID,
        activity_type: str,
        dni_reference: str,
        documents: List[Any],
        quality_result: QualityRuleResult,
        dossier_data: Dict[str, Any],
    ) -> "TriageCase":
        document_ids = {}
        confidence_scores = {}
        for doc in documents:
            document_ids[doc.document_code] = doc.id
            confidence_scores[doc.document_code] = doc.confidence_score or 0.0

        has_missing_docs = any(
            d.field_name.startswith("documents.") for d in quality_result.discrepancies
        )

        if quality_result.is_valid:
            status = TriageStatus.PENDING_REVIEW
            verdict = TriageVerdict.REQUIRES_TRIAGE
        elif has_missing_docs:
            status = TriageStatus.INCOMPLETE
            verdict = TriageVerdict.REQUIRES_TRIAGE
        else:
            status = TriageStatus.PENDING_REVIEW
            verdict = TriageVerdict.REQUIRES_TRIAGE

        case = cls(
            id=uuid4(),
            batch_id=batch_id,
            activity_type=activity_type,
            dni_reference=dni_reference,
            dossier_data=dossier_data,
            # En la creación el "primer JSON" es el propio dossier_data post-LLM.
            original_dossier_data=dossier_data,
            document_ids=document_ids,
            confidence_scores=confidence_scores,
            status=status,
            verdict=verdict,
            discrepancies=quality_result.discrepancies,
        )

        # La ruta touchless passa por `approve()` en vez de dejar APPROVED en el
        # constructor. Antes se seteaba el estado a mano acá, y eso se saltaba dos
        # cosas de `approve()`: `completed_at`/`resolved_at` (que quedaban en None
        # y vaciaban el export de tesis justo en los casos automáticos) y el
        # registro del evento que carga al beneficiario en el maestro.
        if quality_result.is_valid:
            case.approve(None)  # touchless: sin usuario, veredicto AUTO_APPROVED

        return case

    def assign_to_reviewer(self, reviewer_id: UUID) -> None:
        self.status = TriageStatus.IN_REVIEW
        self.resolved_by = reviewer_id
        self.updated_at = datetime.now(timezone.utc)

    def submit_correction(self, corrected_data: Dict[str, Any], corrected_by: UUID) -> None:
        self.dossier_data = corrected_data
        self.status = TriageStatus.CORRECTED
        self.resolved_by = corrected_by
        self.updated_at = datetime.now(timezone.utc)

    def update_discrepancies(self, discrepancies: List[FieldDiscrepancy]) -> None:
        self.discrepancies = list(discrepancies)
        self.updated_at = datetime.now(timezone.utc)

    def approve(self, approved_by: Optional[UUID] = None) -> None:
        # Un caso ya aprobado no vuelve a anunciarse. Sin este guard, una segunda
        # llamada sobre el mismo caso (p. ej. `create_from_quality_result` aprueba
        # y después el caso 6 de la tabla DNI vuelve a aprobar) publicaría dos
        # eventos y sincronizaría dos veces al beneficiario.
        already_approved = self.status == TriageStatus.APPROVED

        self.status = TriageStatus.APPROVED
        # MANUALLY_APPROVED si hay usuario, AUTO_APPROVED si es touchless (approved_by=None)
        self.verdict = TriageVerdict.MANUALLY_APPROVED if approved_by else TriageVerdict.AUTO_APPROVED
        self.resolved_by = approved_by
        now = datetime.now(timezone.utc)
        self.resolved_at = now
        self.completed_at = now
        self.updated_at = now

        if already_approved:
            return

        # Anuncia la aprobación para que el maestro de beneficiarios se actualice.
        #
        # Antes esta lista nunca reciba nada: los 4 bucles que la despachaban
        # (`submit_correction`, `reject_dossier`, `reject_batch`, `dossier_processor`)
        # iteraban siempre un `[]`, así que `handle_mdm_dossier_approved` no se
        # ejecutaba nunca y el beneficiario solo llegaba al maestro por el atajo
        # de `POST /batch/{id}/verify-completion`.
        #
        # Se registra un COPIO profunda de `dossier_data` (no la referencia) porque
        # la capa de aplicación sigue mutando el caso después de aprobar, y el bus
        # se despacha más tarde: con la referencia, el evento viajaría con datos
        # que ya no son los aprobados. `copy.deepcopy` y no `dict()`: este dossier
        # es anidado (beneficiary, related_adults.adults[]), y una copia superficial
        # comparte los dicts internos, que sí se siguen mutando.
        self._pending_events.append(
            DossierApprovedEvent(
                triage_case_id=self.id,
                batch_id=self.batch_id,
                activity_type=self.activity_type,
                dni_reference=self.dni_reference,
                dossier_data=copy.deepcopy(self.dossier_data or {}),
                approved_by=approved_by or SYSTEM_ACTOR_UUID,
            )
        )

    def reassign_id(self, new_id: UUID) -> None:
        """Re-keyea el caso al reprocesar un expediente que ya existe.

        Importante: hay que rehacer los eventos ya registrados. `approve()` los
        guarda con el id que tenía el caso en ese momento, y al reasignar el id
        quedan apuntando al anterior. `DossierApprovedEvent` es un dataclass
        congelado, así que no se puede mutar: se reconstruyen.

        Sin esto, el handler de MDM corre su `UPDATE sync_status = 'SYNCED'`
        sobre un id inexistente: 0 filas afectadas, sin error ni log. El
        beneficiario queda cargado en `persons` (el `dossier_data` del evento sí
        era correcto) pero el caso se queda en PENDING para siempre, y
        `retry-sync` lo reintenta en bucle sin éxito posible.
        """
        self.id = new_id
        self._pending_events = [
            DossierApprovedEvent(
                triage_case_id=new_id,
                batch_id=e.batch_id,
                activity_type=e.activity_type,
                dni_reference=e.dni_reference,
                dossier_data=e.dossier_data,
                approved_by=e.approved_by,
            )
            if isinstance(e, DossierApprovedEvent) else e
            for e in self._pending_events
        ]

    def reject(self, rejected_by: UUID, reason: str) -> None:
        self.status = TriageStatus.REJECTED
        self.verdict = TriageVerdict.MANUALLY_REJECTED
        self.rejection_reason = reason
        self.resolved_by = rejected_by
        self.resolved_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    @property
    def is_finalized(self) -> bool:
        return self.status in (TriageStatus.APPROVED, TriageStatus.REJECTED)

    @property
    def pending_events(self) -> List[Any]:
        return list(self._pending_events)

    def clear_events(self) -> None:
        self._pending_events.clear()

    @property 
    def min_confidence_score(self) -> float:
        scores = [s for s in self.confidence_scores.values() if s is not None]
        return min(scores) if scores else 0.0
