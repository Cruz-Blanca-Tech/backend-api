

from src.contexts.data_quality_triage.application.normalizers.type.bool_normalizer import BoolNormalizer
from src.contexts.data_quality_triage.application.normalizers.type.date_normalizer import DateNormalizer
from src.contexts.data_quality_triage.application.normalizers.type.default_normalizer import DefaultNormalizer
from src.contexts.data_quality_triage.application.normalizers.type.dni_normalizer import DniNormalizer
from src.contexts.data_quality_triage.application.normalizers.type.int_normalizer import IntNormalizer
from src.contexts.data_quality_triage.application.normalizers.type.string_normalizer import StringNormalizer
from src.contexts.data_quality_triage.domain.value_objects.field_mapping import DataType

from src.contexts.data_quality_triage.application.normalizers.type.name_normalizer import NameNormalizer

class NormalizerRegistry:

    def __init__(self):
        self._map = {
            DataType.DNI: DniNormalizer(),
            DataType.STRING: StringNormalizer(),
            DataType.DATE: DateNormalizer(),
            DataType.INT: IntNormalizer(),
            DataType.BOOL: BoolNormalizer(),
            DataType.NAME: NameNormalizer(),
        }

    def get(self, data_type):
        return self._map.get(data_type, DefaultNormalizer())