from dataclasses import dataclass

from enum import Enum

class DataType(str, Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    DATE = "date"
    DNI = "dni"
    BOOL = "bool"
    NAME = "name"
    GENDER = "gender"


@dataclass(frozen=True)
class FieldMapping:
    source_name: str
    domain_name: str
    data_type: DataType