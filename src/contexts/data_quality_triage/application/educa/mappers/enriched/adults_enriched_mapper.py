from typing import List
from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedAdult
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

class AdultsEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: FinsRaw) -> List[EnrichedAdult]:
        adults = []
        
        # Father
        f_dni = self.build_field(raw_dto.parents_father_dni, "DNI Padre", DataType.DNI)
        f_name = self.build_field(raw_dto.parents_father_full_name, "Padre", DataType.NAME)
        if f_dni.raw_value or f_name.raw_value:
            adults.append(EnrichedAdult("FATHER", f_dni, f_name))
            
        # Mother
        m_dni = self.build_field(raw_dto.parents_mother_dni, "DNI Madre", DataType.DNI)
        m_name = self.build_field(raw_dto.parents_mother_full_name, "Madre", DataType.NAME)
        if m_dni.raw_value or m_name.raw_value:
            adults.append(EnrichedAdult("MOTHER", m_dni, m_name))
            
        # Guardian
        g_dni = self.build_field(raw_dto.parents_guardian_dni, "DNI Apoderado", DataType.DNI)
        g_name = self.build_field(raw_dto.parents_guardian_full_name, "Apoderado", DataType.NAME)
        if g_dni.raw_value or g_name.raw_value:
            adults.append(EnrichedAdult("OTHER", g_dni, g_name))
            
        return adults
