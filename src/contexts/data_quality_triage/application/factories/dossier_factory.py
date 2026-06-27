from typing import Dict, Any

from src.contexts.data_quality_triage.application.mappers.educa_inscription_mapper import EducaInscriptionMapper
from src.contexts.data_quality_triage.domain.value_objects.educa_inscription import EducaInscription
from src.contexts.data_quality_triage.application.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.value_objects.field_mapping import DataType

from src.contexts.data_quality_triage.domain.value_objects.raw_data.fins_raw import FichaInscripcionRaw
from src.contexts.data_quality_triage.domain.value_objects.raw_data.dj_raw import DeclaracionJuradaRaw
from src.contexts.data_quality_triage.domain.value_objects.raw_data.dni_raw import DniRaw

class DossierFactory:
    
    @staticmethod
    def from_data(raw_docs: Dict[str, Dict[str, Any]]) -> EducaInscription:
        """
        Crea un DossierData (EducaInscription) a partir de los documentos en crudo.
        raw_docs debe ser un diccionario con los códigos de documento como claves.
        """
        registry = NormalizerRegistry()
        mapper = EducaInscriptionMapper(registry)
        
        # Instantiate strictly typed schemas
        fins_raw = FichaInscripcionRaw(**(raw_docs.get("FINS") or {}))
        dj_raw = DeclaracionJuradaRaw(**(raw_docs.get("DJ") or {}))
        dnibef_raw = DniRaw(**(raw_docs.get("DNIBEF") or {}))
        dniap_raw = DniRaw(**(raw_docs.get("DNIAP") or {}))

        # Mapeo de sub-objetos
        beneficiary = mapper.map_beneficiary(fins_raw)
        parents = mapper.map_parents(fins_raw)
        education = mapper.map_education(fins_raw)
        medical = mapper.map_medical(fins_raw)

        dni_norm = registry.get(DataType.DNI)
        name_norm = registry.get(DataType.NAME)

        # Fallback Apoderado logic: If FINS has no Apoderado, use DNIAP document.
        if not parents.apoderado_type and dniap_raw.DocumentNumber:
            from src.contexts.data_quality_triage.domain.value_objects.parent_detail import ParentDetail
            parents.apoderado_type = "guardian"
            parents.guardian = ParentDetail(
                dni=dni_norm.normalize(dniap_raw.DocumentNumber),
                full_name=name_norm.normalize(f"{dniap_raw.FirstName or ''} {dniap_raw.LastName or ''}".strip()),
                phone=None
            )

        # Construir y validar el objeto principal
        inscription = EducaInscription(
            beneficiary=beneficiary,
            parents=parents,
            education=education,
            medical=medical
        )

        inscription.validate_dossier()

        return inscription
