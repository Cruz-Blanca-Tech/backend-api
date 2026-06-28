from src.contexts.data_quality_triage.application.shared.mappers.base_enriched_mapper import BaseEnrichedMapper
from src.contexts.data_quality_triage.domain.shared.value_objects.field_mapping import DataType
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedAddress
from src.contexts.data_quality_triage.application.educa.dtos.raw.fins_raw import FinsRaw

class AddressEnrichedMapper(BaseEnrichedMapper):
    def map(self, raw_dto: FinsRaw) -> EnrichedAddress:
        return EnrichedAddress(
            lot=self.build_field(raw_dto.address_lot, "Lote", DataType.STRING),
            block=self.build_field(raw_dto.address_block, "Manzana", DataType.STRING),
            city=self.build_field(raw_dto.address_city, "Ciudad", DataType.STRING),
            district=self.build_field(raw_dto.address_district, "Distrito", DataType.STRING),
            neighborhood=self.build_field(raw_dto.address_neighborhood, "Urbanización", DataType.STRING)
        )
