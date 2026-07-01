from typing import List
from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedAdult
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

from src.contexts.data_quality_triage.domain.shared.value_objects.adult_role import AdultRole

class AdultsEnrichedMapper(BaseEnrichedMapper):
    def _split_full_name(self, full_name: str) -> tuple[str, str]:
        if not full_name:
            return "", ""
            
        parts = full_name.strip().split()
        if len(parts) == 1:
            return parts[0], ""
        elif len(parts) == 2:
            return parts[0], parts[1]
        elif len(parts) == 3:
            return parts[0], f"{parts[1]} {parts[2]}"
        else:
            first_name = " ".join(parts[:-2])
            last_name = " ".join(parts[-2:])
            return first_name, last_name

    def map(self, raw_dto: FinsRaw) -> List[EnrichedAdult]:
        adults = []
        
        # Father
        f_dni = self.build_field(raw_dto.parents_father_dni, "DNI Padre", DataType.DNI)
        f_first, f_last = self._split_full_name(raw_dto.parents_father_full_name or "")
        f_first_field = self.build_field(f_first, "Nombres Padre", DataType.NAME)
        f_last_field = self.build_field(f_last, "Apellidos Padre", DataType.NAME)
        f_phone = self.build_field(raw_dto.parents_father_phone, "Teléfono Padre", DataType.PHONE)
        if f_dni.raw_value or f_first or f_last or f_phone.raw_value:
            adults.append(EnrichedAdult(AdultRole.FATHER, f_dni, f_first_field, f_last_field, f_phone))
            
        # Mother
        m_dni = self.build_field(raw_dto.parents_mother_dni, "DNI Madre", DataType.DNI)
        m_first, m_last = self._split_full_name(raw_dto.parents_mother_full_name or "")
        m_first_field = self.build_field(m_first, "Nombres Madre", DataType.NAME)
        m_last_field = self.build_field(m_last, "Apellidos Madre", DataType.NAME)
        m_phone = self.build_field(raw_dto.parents_mother_phone, "Teléfono Madre", DataType.PHONE)
        if m_dni.raw_value or m_first or m_last or m_phone.raw_value:
            adults.append(EnrichedAdult(AdultRole.MOTHER, m_dni, m_first_field, m_last_field, m_phone))
            
        # Guardian
        g_dni = self.build_field(raw_dto.parents_guardian_dni, "DNI Apoderado", DataType.DNI)
        g_first, g_last = self._split_full_name(raw_dto.parents_guardian_full_name or "")
        g_first_field = self.build_field(g_first, "Nombres Apoderado", DataType.NAME)
        g_last_field = self.build_field(g_last, "Apellidos Apoderado", DataType.NAME)
        g_phone = self.build_field(raw_dto.parents_guardian_phone, "Teléfono Apoderado", DataType.PHONE)
        if g_dni.raw_value or g_first or g_last or g_phone.raw_value:
            adults.append(EnrichedAdult(AdultRole.OTHER, g_dni, g_first_field, g_last_field, g_phone))
            
            
        return adults
