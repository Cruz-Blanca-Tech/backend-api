from typing import Dict, Any

from src.contexts.data_quality_triage.domain.educa.value_objects.educa_inscription import EducaInscription
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.application.educa.mappers.educa_inscription_mapper import EducaInscriptionMapper

from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.fins_raw import FichaInscripcionRaw
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.dj_raw import DeclaracionJuradaRaw
from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.dni_raw import DniRaw

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
        dnibef_raw = DniRaw(**(raw_docs.get("DNIBE") or {}))
        dniap_raw = DniRaw(**(raw_docs.get("DNIAP") or {}))

        # Mapeo de sub-objetos
        beneficiary = mapper.map_beneficiary(fins_raw)
        related_adults = mapper.map_parents(fins_raw)
        education = mapper.map_education(fins_raw)
        medical = mapper.map_medical(fins_raw)

        dni_norm = registry.get(DataType.DNI)
        name_norm = registry.get(DataType.NAME)

        # Fallback Apoderado logic: If FINS has no guardian_dni, use DNIAP document.
        if not related_adults.guardian_dni and dniap_raw.DocumentNumber:
            dni_val = dni_norm.normalize(dniap_raw.DocumentNumber)
            related_adults.guardian_dni = dni_val
            
            # Verificar si este DNI ya existe en la lista
            if not any(a.dni == dni_val for a in related_adults.adults):
                from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult
                related_adults.adults.append(RelatedAdult(
                    relationship="OTHER",
                    dni=dni_val,
                    full_name=name_norm.normalize(f"{dniap_raw.FirstName or ''} {dniap_raw.LastName or ''}".strip())
                ))

        # Construir y validar el objeto principal
        inscription = EducaInscription(
            beneficiary=beneficiary,
            related_adults=related_adults,
            education=education,
            medical=medical
        )

        return inscription
