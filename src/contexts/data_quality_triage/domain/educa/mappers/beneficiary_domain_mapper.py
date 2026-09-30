from typing import Optional, Any
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData


class BeneficiaryDomainMapper:
    def map(self, enriched_fins: EnrichedFins, enriched_dnibe: Any = None) -> BeneficiaryData:
        return BeneficiaryData(
            first_name=enriched_fins.child_first_name.normalized_value,
            last_name=enriched_fins.child_last_name.normalized_value,
            dni=enriched_fins.child_dni.normalized_value,
            birth_date=enriched_fins.child_birth_date.normalized_value,
            gender=enriched_fins.child_gender.normalized_value,
            age=enriched_fins.child_age.normalized_value,
            address=self._build_address(enriched_fins, enriched_dnibe),
        )

    @staticmethod
    def _build_address(enriched_fins: EnrichedFins, enriched_dnibe: Any = None) -> Optional[str]:
        def _val(field) -> str:
            v = getattr(field, "normalized_value", None) if field else None
            return str(v).strip() if v is not None and str(v).strip() else ""

        addr = getattr(enriched_fins, "address", None)
        if addr:
            neighborhood = _val(getattr(addr, "neighborhood", None))
            block = _val(getattr(addr, "block", None))
            lot = _val(getattr(addr, "lot", None))
            district = _val(getattr(addr, "district", None))
            city = _val(getattr(addr, "city", None))

            street_parts = []
            if neighborhood:
                street_parts.append(neighborhood)
            if block:
                street_parts.append(block if block.lower().startswith("mz") else f"Mz. {block}")
            if lot:
                street_parts.append(lot if lot.lower().startswith(("lt", "lote")) else f"Lt. {lot}")

            loc_parts = []
            if district:
                loc_parts.append(district)
            if city and city.lower() != district.lower():
                loc_parts.append(city)

            street_str = " ".join(street_parts)
            loc_str = " - ".join(loc_parts)

            if street_str and loc_str:
                return f"{street_str}, {loc_str}"
            if street_str:
                return street_str
            if loc_str:
                return loc_str

        if enriched_dnibe is not None:
            dni_addr = _val(getattr(enriched_dnibe, "address", None))
            if dni_addr:
                return dni_addr

        return None


