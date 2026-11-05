"""D13 (RF-06): en la bandeja, un umbral 0.0 de la DJ debe respetarse (no leerse
como 0.80) y min_confidence_score no debe incluir a la DJ (umbral 0.0 = no se
evalúa por confianza).

Se prueban el cálculo real de GetCasesByBatchUseCase._effective_threshold y la
propiedad TriageCase.min_confidence_score. Contraste: sin umbrales definidos, se
usa el default 0.80. Datos ficticios.
"""
from uuid import uuid4

from src.contexts.data_quality_triage.application.shared.use_cases.get_cases_by_batch_use_case import GetCasesByBatchUseCase
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict

UMBRALES = {"FINS": 0.75, "DNIBE": 0.70, "DNIAP": 0.70, "DJ": 0.0}
SCORES = {"FINS": 0.90, "DNIBE": 0.95, "DNIAP": 0.92, "DJ": 0.30}


def _case(scores):
    return TriageCase(id=uuid4(), batch_id=uuid4(), activity_type="EDUCA_INSCRIPTION", dni_reference="12345678",
                      dossier_data={}, document_ids={}, confidence_scores=dict(scores),
                      status=TriageStatus.PENDING_REVIEW, verdict=TriageVerdict.REQUIRES_TRIAGE, discrepancies=[])


class TestD13UmbralDjBandeja:
    def test_umbral_0_de_la_dj_se_respeta(self):
        umbral = GetCasesByBatchUseCase(triage_repo=None)._effective_threshold(_case(SCORES), UMBRALES)
        assert umbral == 0.75, (
            f"HALLAZGO (D13): con umbrales {UMBRALES}, la bandeja muestra umbral {umbral}: el 0.0 de la DJ se lee "
            "como 0.80 (thresholds.get(code) or 0.80) y pasa a ser el umbral más exigente.")

    def test_min_confidence_excluye_la_dj(self):
        minimo = _case(SCORES).min_confidence_score
        assert minimo == 0.90, (
            f"HALLAZGO (D13): min_confidence_score = {minimo}: incluye la confianza de la DJ (0.30), cuyo umbral es 0.0.")

    def test_contraste_sin_umbrales_usa_default(self):
        assert GetCasesByBatchUseCase(triage_repo=None)._effective_threshold(_case(SCORES), {}) == 0.80
