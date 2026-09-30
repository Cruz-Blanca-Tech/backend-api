from dataclasses import dataclass
from typing import Optional, Any
from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.shared.value_objects.enriched_field import EnrichedField
from src.contexts.data_quality_triage.application.educa.dtos.raw.dni_raw import DniRaw

@dataclass
class EnrichedDni:
    document_number: EnrichedField
    first_name: EnrichedField
    last_name: EnrichedField
    date_of_birth: EnrichedField
    address: Optional[EnrichedField] = None

class DniEnrichedMapper(BaseEnrichedMapper):
    @staticmethod
    def _format_raw_address(raw_addr: Any) -> Optional[str]:
        if not raw_addr:
            return None
        if isinstance(raw_addr, str):
            return raw_addr.strip() or None
        if isinstance(raw_addr, dict):
            parts = [
                str(raw_addr.get(k)).strip()
                for k in ("street_address", "streetAddress", "road", "house_number", "houseNumber", "suburb", "city_district", "city", "state")
                if raw_addr.get(k) and str(raw_addr.get(k)).strip()
            ]
            if parts:
                return ", ".join(dict.fromkeys(parts))
            content = raw_addr.get("content") or raw_addr.get("value")
            if isinstance(content, str) and content.strip():
                return content.strip()
        return None

    def map(self, raw_dto: DniRaw) -> EnrichedDni:
        addr_str = self._format_raw_address(getattr(raw_dto, "address", None))
        return EnrichedDni(
            document_number=self.build_field(raw_dto.document_number, "Número de Documento", DataType.DNI),
            first_name=self.build_field(raw_dto.first_name, "Nombres", DataType.NAME),
            last_name=self.build_field(raw_dto.last_name, "Apellidos", DataType.NAME),
            date_of_birth=self.build_field(raw_dto.date_of_birth, "Fecha de Nacimiento", DataType.DATE),
            address=self.build_field(addr_str, "Dirección", DataType.STRING)
        )

