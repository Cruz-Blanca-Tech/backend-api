import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from src.contexts.data_quality_triage.domain.educa.rules.document.confidence_rules import OcrConfidenceRule
from src.contexts.data_quality_triage.domain.shared.strategies.inscription_strategy import InscriptionTriageStrategy
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.value_objects.triage_status import TriageStatus, TriageVerdict


def _doc(code: str, confidence: float) -> DocumentDTO:
    return DocumentDTO(
        id=uuid4(),
        file_name=f"x_{code}.jpg",
        document_code=code,
        extracted_data={},
        confidence_score=confidence,
    )


def _issues_with_field(issues, field_name: str):
    return [d for d in issues if d.field_name == field_name]


# --------------------------------------------------------------------------
# OcrConfidenceRule: unidad
# --------------------------------------------------------------------------

def test_confidence_rule_flags_docs_below_global_threshold():
    rule = OcrConfidenceRule({"DJ": 0.45, "FINS": 0.65}, 0.60)
    issues = rule.evaluate()
    assert len(issues) == 1
    assert issues[0].field_name == "general_confidence"
    assert issues[0].document_code == "DJ"
    assert issues[0].severity == "WARNING"
    assert issues[0].expected_pattern == ">= 0.6"
    assert issues[0].actual_value == "0.45"


def test_confidence_rule_boundary_not_flagged():
    # score == umbral es válido (se usa <, no <=)
    rule = OcrConfidenceRule({"DJ": 0.60}, 0.60)
    assert rule.evaluate() == []


def test_confidence_rule_per_doc_thresholds():
    threshold_by_code = {"DJ": 0.55, "DNIAP": 0.65, "DNIBE": 0.65}
    scores = {"DJ": 0.45, "FINS": 0.70, "DNIAP": 0.80, "DNIBE": 0.60}
    issues = OcrConfidenceRule(scores, threshold_by_code).evaluate()
    flagged = {(d.document_code, d.actual_value) for d in issues}
    # DJ baja (0.45 < 0.55) y DNIBE baja (0.60 < 0.65); FINS sin umbral se omite;
    # DNIAP 0.80 >= 0.65 ok.
    assert flagged == {("DJ", "0.45"), ("DNIBE", "0.6")}


def test_confidence_rule_ignores_none_scores():
    rule = OcrConfidenceRule({"DJ": None, "FINS": 0.9}, 0.60)
    assert rule.evaluate() == []


def test_confidence_rule_empty_scores():
    assert OcrConfidenceRule({}, 0.60).evaluate() == []


# --------------------------------------------------------------------------
# InscriptionTriageStrategy: cableado de la regla
# --------------------------------------------------------------------------

def _make_strategy():
    strategy = InscriptionTriageStrategy()
    # Aislamos la estrategia: mapper y validator stubs, sin dependencias externas.
    strategy._mapper = MagicMock()
    strategy._mapper.map.return_value = {}
    strategy._validator = MagicMock()
    strategy._validator.validate.return_value = []
    return strategy


def test_strategy_low_confidence_discrepancy_and_triage():
    strategy = _make_strategy()
    case = strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.45), _doc("FINS", 0.90)],
        context={"confidence_thresholds": {"DJ": 0.55, "FINS": 0.60}},
    )

    conf_issues = _issues_with_field(case.discrepancies, "general_confidence")
    assert len(conf_issues) == 1
    assert conf_issues[0].document_code == "DJ"
    assert conf_issues[0].severity == "WARNING"

    # Los scores se propagan al caso (lo que la UI usa como min_confidence_score)
    assert case.confidence_scores == {"DJ": 0.45, "FINS": 0.90}
    assert case.status == TriageStatus.PENDING_REVIEW
    assert case.verdict == TriageVerdict.REQUIRES_TRIAGE


def test_strategy_high_confidence_no_confidence_discrepancy():
    strategy = _make_strategy()
    case = strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.74), _doc("FINS", 0.70)],
        context={"confidence_thresholds": {"DJ": 0.55, "FINS": 0.60}},
    )
    assert _issues_with_field(case.discrepancies, "general_confidence") == []


def test_strategy_single_float_threshold_via_context():
    strategy = _make_strategy()
    case = strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.55), _doc("FINS", 0.70)],
        context={"confidence_threshold": 0.60},
    )
    conf_issues = _issues_with_field(case.discrepancies, "general_confidence")
    assert [d.document_code for d in conf_issues] == ["DJ"]


def test_strategy_default_threshold_when_context_empty():
    strategy = _make_strategy()
    case = strategy.execute(
        batch_id=uuid4(),
        activity_type=ActivityType.EDUCA_INSCRIPTION,
        dni_reference="12345678",
        documents=[_doc("DJ", 0.79)],
        context={},
    )
    assert len(_issues_with_field(case.discrepancies, "general_confidence")) == 1