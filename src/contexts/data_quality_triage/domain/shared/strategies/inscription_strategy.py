from typing import List
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.strategies.base_strategy import TriageStrategy
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode
from src.contexts.data_quality_triage.domain.educa.rules.document.educa_document_rules_validator import EducaDocumentRulesValidator
from src.contexts.data_quality_triage.application.educa.mappers.enriched.educa_raw_to_enriched_mapper import EducaRawToEnrichedMapper
from src.contexts.data_quality_triage.application.shared.factories.dossier_factory import DossierFactory
from src.contexts.data_quality_triage.domain.shared.value_objects.activity_type import ActivityType
from src.contexts.data_quality_triage.domain.shared.entities.triage_case import TriageCase
from uuid import UUID


class InscriptionTriageStrategy(TriageStrategy):
    """
    Estrategia de validación para el flujo de Inscripción Educa.
    Orquesta dos pasos:
      1. Raw → Enriched  (EducaRawToEnrichedMapper)
      2. Validación de documentos  (EducaDocumentRulesValidator)
    """

    def __init__(self):
        self._mapper    = EducaRawToEnrichedMapper()
        self._validator = EducaDocumentRulesValidator()

    def execute(
        self,
        batch_id: UUID,
        activity_type: ActivityType,
        dni_reference: str,
        documents: List[DocumentDTO]
    ) -> TriageCase:

        enriched_docs = self._mapper.map(documents)

        discrepancies = self._validator.validate(
            enriched_docs=enriched_docs
        )
        
        try:
            domain_entity = DossierFactory.create_from_enriched(
                activity_type=activity_type,
                **enriched_docs
            )
            from dataclasses import asdict
            dossier_data = asdict(domain_entity)
            is_complete, domain_issues = domain_entity.validate_completeness()
            if not is_complete:
                discrepancies.extend(domain_issues)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error construyendo entidad de dominio para batch {batch_id}, dni {dni_reference}: {e}")
            from src.contexts.data_quality_triage.domain.shared.value_objects.field_discrepancy import FieldDiscrepancy
            discrepancies.append(FieldDiscrepancy(
                field_name="domain_entity",
                expected_pattern="Entidad válida",
                actual_value="Error",
                rule_description=f"Excepción al crear la entidad de dominio: {str(e)}",
                severity="ERROR"
            ))
            dossier_data = {}

        has_errors = any(d.severity == "ERROR" for d in discrepancies)

        result = QualityRuleResult(
            is_valid=not has_errors,
            discrepancies=discrepancies,
            confidence_passed=True,
            enriched_docs=enriched_docs,
        )
        
        return TriageCase.create_from_quality_result(
            batch_id=batch_id,
            activity_type=activity_type.value,
            dni_reference=dni_reference,
            documents=documents,
            quality_result=result,
            dossier_data=dossier_data,
        )

