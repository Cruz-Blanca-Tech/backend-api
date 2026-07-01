from enum import Enum

class AdultRole(str, Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    TUTOR = "TUTOR"
    OTHER = "OTHER"
