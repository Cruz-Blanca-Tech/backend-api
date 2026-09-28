from typing import List
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO
from src.contexts.data_quality_triage.domain.shared.strategies.base_strategy import TriageStrategy
from src.contexts.data_quality_triage.domain.shared.value_objects.quality_rule_result import QualityRuleResult
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode
from src.contexts.data_quality_triage.domain.educa.rules.document.educa_document_rules_validator import EducaDocumentRulesValidator
from src.contexts.data_quality_triage.domain.educa.rules.document.confidence_rules import OcrConfidenceRule
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

    async def execute(
        self,
        batch_id: UUID,
        activity_type: ActivityType,
        dni_reference: str,
        documents: List[DocumentDTO],
        context: dict = None
    ) -> TriageCase:

        enriched_docs = self._mapper.map(documents)

        discrepancies = self._validator.validate(
            enriched_docs=enriched_docs
        )

        # Regla de confianza OCR: evalúa la calidad del escaneo contra el umbral
        # mínimo por documento. El/los umbral(es) llegan por contexto desde el
        # dossier_processor, que los lee de activity_requirements (calibración por
        # tipo de documento y por actividad). Si no llegan, se usa el default 0.80.
        # Un documento bajo el umbral genera una WARNING → REQUIRES_TRIAGE.
        #
        # Solo entran los documentos que de verdad pasaron por el OCR, y la señal
        # es `confidence_score IS NOT NULL` (lo escribe `mark_as_processed_
        # successfully`; Azure siempre devuelve confidence). Un documento con
        # score NULL nunca se escaneó: o su expediente está incompleto y el
        # intake lo dejó PENDING a la espera del que falta, o el OCR falló.
        # Inventarle un 0 a ese documento produce un WARNING engañoso de
        # "escaneo de mala calidad" sobre algo que no se escaneó, y encima
        # duplica el aviso que de verdad importa: el ERROR de
        # `RequiredDocumentsRule` que nombra el documento que falta.
        confidence_scores = {
            (doc.document_code or "UNKNOWN"): doc.confidence_score
            for doc in documents
            if doc.confidence_score is not None
        }
        confidence_threshold = (
            (context or {}).get("confidence_thresholds")
            or (context or {}).get("confidence_threshold", 0.80)
        )
        confidence_issues = OcrConfidenceRule(
            confidence_scores=confidence_scores,
            confidence_threshold=confidence_threshold,
        ).evaluate()
        discrepancies.extend(confidence_issues)
        
        try:
            domain_entity = DossierFactory.create_from_enriched(
                activity_type=activity_type,
                context=context or {},
                **enriched_docs
            )

            # AUTO-CORRECCIÓN de apellidos de Padre/Madre corroborada por doble
            # lectura: si el apellido del niño sale idéntico en la FINS y en su
            # DNI (DNIBE), y un adulto trae una variante con error típico de OCR
            # (TAFOR/TAFUR), se corrige el nombre en el dossier y se agrega una
            # nota informativa. Corre ANTES de validate_completeness: la regla de
            # coherencia de apellidos ya ve el apellido unificado y no advierte
            # (falso positivo). Sin corroboración no se corrige nada y la regla
            # sigue advirtiendo como siempre.
            from src.contexts.data_quality_triage.application.shared.services.surname_auto_corrector import SurnameAutoCorrector
            fins = enriched_docs.get(EducaDocumentCode.FINS.value)
            child_dni = (
                enriched_docs.get(EducaDocumentCode.DNI_BENEFICIARY.value)
                or enriched_docs.get(EducaDocumentCode.DNI_GENERIC.value)
            )
            corrections = SurnameAutoCorrector(
                dossier=domain_entity,
                fins_last_name=(
                    fins.child_last_name.normalized_value
                    if fins and fins.child_last_name else None
                ),
                child_dni_last_name=(
                    child_dni.last_name.normalized_value
                    if child_dni and child_dni.last_name else None
                ),
            ).correct()
            discrepancies.extend(corrections)

            # RECONCILIACIÓN DE NOMBRE DEL APODERADO (DNIAP vs FINS vs DNIBE + DJ)
            # Compara apellidos: DNIAP (apoderado), DNIBE (niño), FINS_apoderado, FINS_niño.
            # Gana el que más fuentes respalden; DNIAP y DNIBE son docs oficiales (peso alto).
            from src.contexts.data_quality_triage.application.shared.services.apoderado_name_reconciler import ApoderadoNameReconciler
            dniap = enriched_docs.get(EducaDocumentCode.DNI_APODERADO.value)
            dnibe = enriched_docs.get(EducaDocumentCode.DNI_BENEFICIARY.value)
            dj = enriched_docs.get(EducaDocumentCode.DJ.value)
            if dniap and fins:
                reconciler = ApoderadoNameReconciler(
                    dniap=dniap,
                    fins=fins,
                    dnibe=dnibe,
                    dj=dj,
                    dossier_adults=domain_entity.related_adults.adults,
                )
                apoderado_corrections = reconciler.reconcile()
                discrepancies.extend(apoderado_corrections)

            # LLM NAME RECONCILER (último recurso semántico)
            # Solo si hay WARNINGs de coherencia sin resolver y hay LLM disponible en contexto
            from src.contexts.data_quality_triage.application.shared.services.llm_name_reconciler import LLMNameReconciler
            llm_client = context.get("llm_client") if context else None
            deployment_name = "gpt-4o-mini"  # deployment por defecto
            if llm_client and dniap and fins:
                # Buscar WARNINGs de coherencia sin resolver
                coherence_warnings = [
                    d for d in discrepancies
                    if d.severity == "WARNING" and ("coherencia" in d.field_name.lower() or "apellido" in d.rule_description.lower())
                ]
                if coherence_warnings:
                    llm_reconciler = LLMNameReconciler(
                        llm_client=llm_client,
                        deployment_name=deployment_name,
                        dniap=dniap,
                        fins=fins,
                        dnibe=dnibe,
                        dj=dj,
                        dossier_adults=domain_entity.related_adults.adults,
                    )
                    llm_corrections = await llm_reconciler.reconcile(coherence_warnings)
                    discrepancies.extend(llm_corrections)

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
            from dataclasses import asdict
            fallback_entity = DossierFactory.create_empty(activity_type)
            dossier_data = asdict(fallback_entity)

        has_errors = any(d.severity == "ERROR" for d in discrepancies)
        has_warnings = any(d.severity == "WARNING" for d in discrepancies)

        result = QualityRuleResult(
            is_valid=(not has_errors and not has_warnings),
            discrepancies=discrepancies,
            confidence_passed=(not confidence_issues),
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

