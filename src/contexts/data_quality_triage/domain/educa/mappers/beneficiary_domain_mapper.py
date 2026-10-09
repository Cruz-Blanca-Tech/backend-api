from typing import Optional, Any
from src.contexts.data_quality_triage.domain.educa.value_objects.enriched_data import EnrichedFins
from src.contexts.data_quality_triage.domain.educa.value_objects.beneficiary_data import BeneficiaryData
from src.contexts.data_quality_triage.domain.educa.services.name_separator import separate_child_name_and_surnames


class BeneficiaryDomainMapper:
    def map(self, enriched_fins: EnrichedFins, enriched_dnibe: Any = None, related_adults: Any = None) -> BeneficiaryData:
        # Extraer nombres completos de padre y madre para la separación inteligente
        father_name = None
        mother_name = None
        if related_adults and hasattr(related_adults, "adults"):
            for a in related_adults.adults:
                rel = getattr(a, "relationship", "")
                rel_str = rel.value if hasattr(rel, "value") else str(rel)
                if "FATHER" in rel_str.upper() or "PADRE" in rel_str.upper():
                    father_name = getattr(a, "full_name", None)
                elif "MOTHER" in rel_str.upper() or "MADRE" in rel_str.upper():
                    mother_name = getattr(a, "full_name", None)

        if not father_name or not mother_name:
            for a in (getattr(enriched_fins, "adults", []) or []):
                rel = getattr(a, "role", "")
                rel_str = rel.value if hasattr(rel, "value") else str(rel)
                fn_val = getattr(getattr(a, "first_name", None), "normalized_value", "") or ""
                ln_val = getattr(getattr(a, "last_name", None), "normalized_value", "") or ""
                full = f"{fn_val} {ln_val}".strip()
                if ("FATHER" in rel_str.upper() or "PADRE" in rel_str.upper()) and not father_name:
                    father_name = full
                elif ("MOTHER" in rel_str.upper() or "MADRE" in rel_str.upper()) and not mother_name:
                    mother_name = full

        raw_first_name = enriched_fins.child_first_name.normalized_value if enriched_fins.child_first_name else None
        raw_last_name = enriched_fins.child_last_name.normalized_value if enriched_fins.child_last_name else None

        # Si el DNI oficial del beneficiario tiene nombres y FINS estaba vacío o contenía dígitos de OCR:
        dnibe_fn = getattr(getattr(enriched_dnibe, "first_name", None), "normalized_value", None)
        dnibe_ln = getattr(getattr(enriched_dnibe, "last_name", None), "normalized_value", None)
        if dnibe_fn and (not raw_first_name or any(c.isdigit() for c in str(raw_first_name))):
            raw_first_name = dnibe_fn
        if dnibe_ln and (not raw_last_name or any(c.isdigit() for c in str(raw_last_name))):
            raw_last_name = dnibe_ln

        # Fallback para DNI del beneficiario si FINS vino vacío
        dnibe_dni = getattr(getattr(enriched_dnibe, "document_number", None), "normalized_value", None)
        raw_dni = enriched_fins.child_dni.normalized_value if enriched_fins.child_dni else None
        if not raw_dni and dnibe_dni:
            raw_dni = dnibe_dni

        # Fallback para Fecha de Nacimiento si FINS vino vacío
        dnibe_dob = getattr(getattr(enriched_dnibe, "date_of_birth", None), "normalized_value", None)
        raw_dob = enriched_fins.child_birth_date.normalized_value if enriched_fins.child_birth_date else None
        if not raw_dob and dnibe_dob:
            raw_dob = dnibe_dob

        sep_first_name, sep_last_name = separate_child_name_and_surnames(
            raw_first_name,
            raw_last_name,
            father_full_name=father_name,
            mother_full_name=mother_name
        )

        return BeneficiaryData(
            first_name=sep_first_name,
            last_name=sep_last_name,
            dni=raw_dni,
            birth_date=raw_dob,
            gender=enriched_fins.child_gender.normalized_value if enriched_fins.child_gender else None,
            age=enriched_fins.child_age.normalized_value if enriched_fins.child_age else None,
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


