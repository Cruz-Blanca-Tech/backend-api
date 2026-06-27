from typing import Any, Dict
from src.contexts.data_quality_triage.application.shared.services.normalize_registry import NormalizerRegistry
from src.contexts.data_quality_triage.domain.educa.value_objects.family_data import FamilyData
from src.contexts.data_quality_triage.domain.educa.value_objects.related_adult import RelatedAdult
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType

from src.contexts.data_quality_triage.domain.educa.value_objects.raw_data.fins_raw import FichaInscripcionRaw

class ParentsMapper:
    def __init__(self, registry: NormalizerRegistry):
        self.dni_normalizer = registry.get(DataType.DNI)
        self.name_normalizer = registry.get(DataType.NAME)

    def map(self, fins_raw: FichaInscripcionRaw) -> FamilyData:
        if not fins_raw:
            return FamilyData()
            
        adults = []
        
        # Father
        f_dni = self.dni_normalizer.normalize(fins_raw.parents_father_dni)
        if f_dni or fins_raw.parents_father_full_name:
            adults.append(RelatedAdult(
                relationship="FATHER",
                dni=f_dni,
                full_name=fins_raw.parents_father_full_name,
                phone=fins_raw.parents_father_phone
            ))
            
        # Mother
        m_dni = self.dni_normalizer.normalize(fins_raw.parents_mother_dni)
        if m_dni or fins_raw.parents_mother_full_name:
            adults.append(RelatedAdult(
                relationship="MOTHER",
                dni=m_dni,
                full_name=fins_raw.parents_mother_full_name,
                phone=fins_raw.parents_mother_phone
            ))
            
        # Guardian
        g_dni = self.dni_normalizer.normalize(fins_raw.parents_guardian_dni)
        if g_dni or fins_raw.parents_guardian_full_name:
            adults.append(RelatedAdult(
                relationship="OTHER",
                dni=g_dni,
                full_name=fins_raw.parents_guardian_full_name,
                phone=fins_raw.parents_guardian_phone
            ))
        
        # Si el OCR nos dio explícitamente un "guardian" en FINS, asumimos que ese DNI es el apoderado.
        # Si no, DossierFactory podría decidir poner el DNIAP.
        guardian_dni = g_dni if g_dni else None
        
        return FamilyData(
            adults=adults,
            guardian_dni=guardian_dni
        )
