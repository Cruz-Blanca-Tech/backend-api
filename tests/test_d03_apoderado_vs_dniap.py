"""D3: al guardar la corrección, el apoderado elegido se compara con la copia de su DNI (DNIAP)."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.contexts.data_quality_triage.domain.educa.rules.document.guardian_dniap_rule import guardian_vs_dniap_issue
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus
from src.contexts.data_quality_triage.application.shared.use_cases.submit_correction_use_case import SubmitCorrectionUseCase
from tests.test_reject_duplicate_enrollment import _make_pending_case


def test_coincide_no_hay_observacion():
    assert guardian_vs_dniap_issue("87654321", "87654321") is None


def test_no_coincide_es_error_bloqueante():
    issue = guardian_vs_dniap_issue("87654321", "11223344")
    assert issue is not None
    assert issue.severity == "ERROR"
    assert issue.field_name == "related_adults.guardian"
    assert "11223344" in issue.rule_description


@pytest.mark.parametrize("dniap", [None, "", "1234567", "ABC12345"])
def test_dniap_ilegible_no_se_compara(dniap):
    assert guardian_vs_dniap_issue("87654321", dniap) is None


def _uc(case, dniap_number):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=case)
    repo.save = AsyncMock()
    repo.get_all_by_batch_id = AsyncMock(return_value=[case])
    validator = MagicMock()
    validator.validate_can_be_corrected = AsyncMock()
    beneficiary_repo = MagicMock()
    beneficiary_repo.get_by_dni = AsyncMock(return_value=None)
    session = AsyncMock()
    resultado = MagicMock()
    resultado.fetchone.return_value = (str(uuid4()),)
    session.execute = AsyncMock(return_value=resultado)
    uc = SubmitCorrectionUseCase(triage_repo=repo, session=session,
                                 beneficiary_repo=beneficiary_repo, status_validator=validator)
    uc._load_dniap_number = AsyncMock(return_value=dniap_number)
    return uc


@pytest.mark.asyncio
async def test_apoderado_distinto_al_dniap_no_se_aprueba():
    case = _make_pending_case()  # apoderada: 87654321
    await _uc(case, "11223344").execute(case.id, uuid4(), case.dossier_data)
    assert case.status != TriageStatus.APPROVED
    assert any(d.field_name == "related_adults.guardian" and d.severity == "ERROR" for d in case.discrepancies)


@pytest.mark.asyncio
async def test_apoderado_igual_al_dniap_se_aprueba():
    case = _make_pending_case()
    await _uc(case, "87654321").execute(case.id, uuid4(), case.dossier_data)
    assert case.status == TriageStatus.APPROVED
