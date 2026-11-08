"""D21: restricción única de inscripción y verificación bloqueante."""
from uuid import uuid4

from src.contexts.core_beneficiary_management.infrastructure.persistence.model.enrollment_model import EnrollmentModel
from src.contexts.data_quality_triage.domain.educa.rules.domain.enrollment_rules import unverified_enrollment_issue
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.shared.events.dossier_approved_event import DossierApprovedEvent
from tests.test_reject_duplicate_enrollment import _make_pending_case


def test_la_tabla_tiene_la_restriccion_unica():
    uniques = [tuple(c.name for c in u.columns) for u in EnrollmentModel.__table__.constraints
               if u.__class__.__name__ == "UniqueConstraint"]
    assert ("beneficiary_id", "activity_code") in uniques


def test_retener_un_aprobado_retira_el_evento_y_lo_deja_pendiente():
    case = _make_pending_case()
    case.approve(None)
    assert any(isinstance(e, DossierApprovedEvent) for e in case.pending_events)

    case.hold_for_review(unverified_enrollment_issue("12345678"))

    assert case.status == TriageStatus.PENDING_REVIEW
    assert case.verdict == TriageVerdict.REQUIRES_TRIAGE
    assert not any(isinstance(e, DossierApprovedEvent) for e in case.pending_events)
    assert case.discrepancies[-1].severity == "ERROR"
