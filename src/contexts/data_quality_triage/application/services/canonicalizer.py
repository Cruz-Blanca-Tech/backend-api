# bc3/domain/services/canonicalizer.py

from typing import Dict, Any, List

from src.contexts.data_quality_triage.domain.value_objects.canonical_data import CanonicalData

from ...domain.value_objects.field_mapping import FieldMapping


class Canonicalizer:

    def __init__(self, mappings: List[FieldMapping]):
        self.mappings = mappings


    def build(self, raw: Dict[str, Any]) -> CanonicalData:

        canonical = {}

        for mapping in self.mappings:

            value = raw.get(mapping.source_name)

            canonical[mapping.domain_name] = self._convert(
                value,
                mapping.data_type
            )

        return CanonicalData(canonical)


    def _convert(self, value, data_type: str):

        if value is None:
            return None

        if data_type == "string":
            return str(value)

        if data_type == "int":
            return int(value)

        if data_type == "float":
            return float(value)

        return value