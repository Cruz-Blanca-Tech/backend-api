import pytest
from unittest.mock import MagicMock

from src.contexts.data_quality_triage.domain.educa.rules.document.required_documents_rule import RequiredDocumentsRule
from src.contexts.data_quality_triage.domain.educa.rules.document.educa_document_rules_validator import EducaDocumentRulesValidator
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode

def test_required_documents_rule_all_present():
    rule = RequiredDocumentsRule()
    discrepancies = rule.evaluate(
        enriched_fins=MagicMock(),
        enriched_dj=MagicMock(),
        enriched_dnibe=MagicMock(),
        enriched_dniap=MagicMock(),
    )
    assert len(discrepancies) == 0

def test_required_documents_rule_missing_dnibe():
    rule = RequiredDocumentsRule()
    discrepancies = rule.evaluate(
        enriched_fins=MagicMock(),
        enriched_dj=MagicMock(),
        enriched_dnibe=None,
        enriched_dniap=MagicMock(),
    )
    assert len(discrepancies) == 1
    d = discrepancies[0]
    assert d.field_name == "documents.DNIBE"
    assert d.severity == "ERROR"
    assert d.document_code == "DNIBE"
    assert "DNI del Beneficiario" in d.rule_description

def test_required_documents_rule_missing_dniap():
    rule = RequiredDocumentsRule()
    discrepancies = rule.evaluate(
        enriched_fins=MagicMock(),
        enriched_dj=MagicMock(),
        enriched_dnibe=MagicMock(),
        enriched_dniap=None,
    )
    assert len(discrepancies) == 1
    d = discrepancies[0]
    assert d.field_name == "documents.DNIAP"
    assert d.severity == "ERROR"
    assert d.document_code == "DNIAP"

def test_educa_document_rules_validator_includes_required_rule():
    validator = EducaDocumentRulesValidator()
    # If enriched_docs is empty
    discrepancies = validator.validate(enriched_docs={})
    missing_codes = [d.document_code for d in discrepancies if d.field_name.startswith("documents.")]
    assert set(missing_codes) == {"FINS", "DJ", "DNIBE", "DNIAP"}
