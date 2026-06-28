from typing import Dict, Any, List
from src.contexts.data_quality_triage.domain.shared.dtos.document_dto import DocumentDTO

from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.application.educa.mappers.enriched.fins_enriched_mapper import FinsEnrichedMapper
from src.contexts.data_quality_triage.application.educa.mappers.enriched.dj_enriched_mapper import DjEnrichedMapper
from src.contexts.data_quality_triage.application.educa.mappers.enriched.dni_enriched_mapper import DniEnrichedMapper
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw
from src.contexts.data_quality_triage.application.educa.dtos.raw.dj_raw import DjRaw
from src.contexts.data_quality_triage.application.educa.dtos.raw.dni_raw import DniRaw
from src.contexts.data_quality_triage.domain.educa.value_objects.document_code import EducaDocumentCode


class EducaRawToEnrichedMapper:
    """
    Convierte el diccionario crudo de documentos (indexado por código de documento)
    a sus respectivos objetos Enriched normalizados.
    Usa EducaDocumentCode para no depender de strings literales.
    """

    def __init__(self, registry: NormalizerRegistry = None):
        registry = registry or NormalizerRegistry()
        self._fins = FinsEnrichedMapper(registry)
        self._dj   = DjEnrichedMapper(registry)
        self._dni  = DniEnrichedMapper(registry)

    def map(self, documents: List[DocumentDTO]) -> dict:
        raw_docs = {doc.document_code: doc.extracted_data for doc in documents if doc.document_code}
        
        fins_raw = raw_docs.get(EducaDocumentCode.FINS.value)
        dj_raw   = raw_docs.get(EducaDocumentCode.DJ.value)
        dnibe    = raw_docs.get(EducaDocumentCode.DNI_BENEFICIARY.value)
        dniap    = raw_docs.get(EducaDocumentCode.DNI_APODERADO.value)
        # Some setups send a generic "DNI" code — treat it as beneficiary
        dni_generic = raw_docs.get(EducaDocumentCode.DNI_GENERIC.value)

        return {
            EducaDocumentCode.FINS.value:            self._fins.map(FinsRaw.from_dict(fins_raw)) if fins_raw else None,
            EducaDocumentCode.DJ.value:              self._dj.map(DjRaw.from_dict(dj_raw))       if dj_raw   else None,
            EducaDocumentCode.DNI_BENEFICIARY.value: self._dni.map(DniRaw.from_dict(dnibe))      if dnibe    else None,
            EducaDocumentCode.DNI_APODERADO.value:   self._dni.map(DniRaw.from_dict(dniap))      if dniap    else None,
            EducaDocumentCode.DNI_GENERIC.value:     self._dni.map(DniRaw.from_dict(dni_generic)) if dni_generic else None,
        }
