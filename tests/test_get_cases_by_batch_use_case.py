import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.contexts.data_quality_triage.application.shared.use_cases.get_cases_by_batch_use_case import GetCasesByBatchUseCase
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict
from src.contexts.data_quality_triage.infrastructure.persistence.repositories.sql_triage_repository import SqlTriageRepository


THRESHOLDS_BATCH = {"DJ": 0.45, "FINS": 0.60, "DNIAP": 0.65, "DNIBE": 0.65}


def _make_case(confidence_scores=None) -> TriageCase:
    scores = (
        {"DJ": 0.74, "FINS": 0.70, "DNIAP": 0.75, "DNIBE": 0.72}
        if confidence_scores is None
        else confidence_scores
    )
    return TriageCase(
        id=uuid4(),
        batch_id=uuid4(),
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="11111111",
        dossier_data={},
        document_ids={},
        confidence_scores=scores,
        status=TriageStatus.PENDING_REVIEW,
        verdict=TriageVerdict.REQUIRES_TRIAGE,
        discrepancies=[],
    )


@pytest.mark.asyncio
async def test_execute_expone_umbral_efectivo_real():
    # N2: antes el listado mandaba confidence_threshold=0.0 fijo.
    repo = MagicMock()
    repo.list_by_batch_id = AsyncMock(return_value=([_make_case()], 1))
    repo.get_confidence_thresholds = AsyncMock(return_value=dict(THRESHOLDS_BATCH))
    uc = GetCasesByBatchUseCase(triage_repo=repo)

    resp = await uc.execute(uuid4())

    assert len(resp.items) == 1
    # El umbral más exigente entre los documentos del caso (DJ 0.45, FINS 0.60,
    # DNIAP 0.65, DNIBE 0.65) → 0.65, no 0.0.
    assert resp.items[0].confidence_threshold == 0.65


@pytest.mark.asyncio
async def test_execute_fallback_default_sin_requisitos():
    repo = MagicMock()
    repo.list_by_batch_id = AsyncMock(return_value=([_make_case()], 1))
    repo.get_confidence_thresholds = AsyncMock(return_value={})
    uc = GetCasesByBatchUseCase(triage_repo=repo)

    resp = await uc.execute(uuid4())

    # Sin umbrales en la actividad, se usa el default del engine (0.80).
    assert resp.items[0].confidence_threshold == 0.80


def test_effective_threshold_usa_solo_documentos_presentes():
    uc = GetCasesByBatchUseCase(triage_repo=MagicMock())
    case = _make_case(confidence_scores={"FINS": 0.70})
    assert uc._effective_threshold(case, {"FINS": 0.60}) == 0.60

    # Documentos sin umbral definido → default 0.80.
    case2 = _make_case(confidence_scores={"DNIAP": 0.75})
    assert uc._effective_threshold(case2, {"DJ": 0.45}) == 0.80

    # Sin documentos → default 0.80.
    case3 = _make_case(confidence_scores={})
    assert uc._effective_threshold(case3, dict(THRESHOLDS_BATCH)) == 0.80


@pytest.mark.asyncio
async def test_repository_get_confidence_thresholds_mapea_filas():
    class FakeResult:
        def fetchall(self):
            return [("DJ", 0.45), ("FINS", 0.60), (None, 0.50)]  # filas sin código se descartan

    session = MagicMock()
    session.execute = AsyncMock(return_value=FakeResult())
    repo = SqlTriageRepository(session=session)

    thr = await repo.get_confidence_thresholds(uuid4())

    assert thr == {"DJ": 0.45, "FINS": 0.60}