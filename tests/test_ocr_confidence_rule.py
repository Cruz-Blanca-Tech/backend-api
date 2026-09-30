import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from src.contexts.data_quality_triage.domain.educa.rules.document.confidence_rules import OcrConfidenceRule
from src.contexts.data_quality_triage.domain.shared.strategies.inscription_strategy import InscriptionTriageStrategy
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict


def _doc(code: str, confidence) -> DocumentDTO:
    return DocumentDTO(
        id=uuid4(),
        file_name=f"x_{code}.jpg",
        document_code=code,
        extracted_data={},
        confidence_score=confidence,
    )


def _make_strategy() -> InscriptionTriageStrategy:
    strategy = InscriptionTriageStrategy()
    strategy._mapper = MagicMock()
    strategy._mapper.map.return_value = {}
    strategy._validator = MagicMock()
    strategy._validator.validate.return_value = []
    return strategy


def _issues_with_field(discrepancies, field_name: str):
    return [d for d in discrepancies if d.field_name == field_name]


@pytest.mark.asyncio
async def test_strategy_low_confidence_discrepancy_and_triage():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DNIBE", 0.45), _doc("FINS", 0.90)],
        context={"confidence_thresholds": {"DNIBE": 0.65, "FINS": 0.60}},
    )

    conf_issues = [d for d in case.discrepancies if d.field_name == "general_confidence"]
    assert len(conf_issues) == 1
    # Now consolidated into single GENERAL warning
    assert conf_issues[0].document_code == "GENERAL"
    # Mensaje amigable para el operador (sin códigos internos ni puntajes)
    assert "copia del dni del niño" in conf_issues[0].rule_description.lower()
    assert "revis" in conf_issues[0].rule_description.lower()

    # Los scores se propagan al caso (lo que la UI usa como min_confidence_score)
    assert case.confidence_scores == {"DNIBE": 0.45, "FINS": 0.90}
    assert case.status == TriageStatus.PENDING_REVIEW
    assert case.verdict == TriageVerdict.REQUIRES_TRIAGE


@pytest.mark.asyncio
async def test_strategy_dj_is_excluded_from_confidence_warning():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.35), _doc("FINS", 0.90)],
        context={"confidence_thresholds": {"DJ": 0.65, "FINS": 0.60}},
    )
    conf_issues = [d for d in case.discrepancies if d.field_name == "general_confidence"]
    assert conf_issues == []


@pytest.mark.asyncio
async def test_strategy_high_confidence_no_confidence_discrepancy():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DNIBE", 0.74), _doc("FINS", 0.70)],
        context={"confidence_thresholds": {"DNIBE": 0.65, "FINS": 0.60}},
    )
    conf_issues = [d for d in case.discrepancies if d.field_name == "general_confidence"]
    assert conf_issues == []


@pytest.mark.asyncio
async def test_strategy_single_float_threshold_via_context():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DNIBE", 0.55), _doc("FINS", 0.70)],
        context={"confidence_threshold": 0.60},
    )
    conf_issues = [d for d in case.discrepancies if d.field_name == "general_confidence"]
    # Single consolidated warning
    assert len(conf_issues) == 1
    assert conf_issues[0].document_code == "GENERAL"
    # Mensaje amigable: DNIBE por debajo de 0.60, FINS por encima
    assert "copia del dni del niño" in conf_issues[0].rule_description.lower()
    assert "revis" in conf_issues[0].rule_description.lower()


@pytest.mark.asyncio
async def test_strategy_threshold_dict_vs_float_priority():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DNIBE", 0.55), _doc("FINS", 0.70)],
        context={
            "confidence_thresholds": {"DNIBE": 0.55, "FINS": 0.60},
            "confidence_threshold": 0.60,
        },
    )
    conf_issues = [d for d in case.discrepancies if d.field_name == "general_confidence"]
    # Dict has priority: DNIBE 0.55 -> OK, FINS 0.60 -> OK
    assert [d for d in case.discrepancies if d.field_name == "general_confidence"] == []


@pytest.mark.asyncio
async def test_strategy_missing_threshold_uses_default():
    strategy = _make_strategy()
    case = await strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DNIBE", 0.55), _doc("FINS", 0.70)],
        context={},
    )
    conf_issues = [d for d in case.discrepancies if d.field_name == "general_confidence"]
    # Default 0.80 -> DNIBE 0.55 WARNING, FINS 0.70 WARNING -> consolidated into 1
    assert len(conf_issues) == 1
    assert conf_issues[0].document_code == "GENERAL"
    # Mensaje amigable: ambos documentos por debajo del umbral por defecto
    assert "copia del dni del niño" in conf_issues[0].rule_description.lower()
    assert "ficha de inscripción" in conf_issues[0].rule_description.lower()
    assert "revis" in conf_issues[0].rule_description.lower()