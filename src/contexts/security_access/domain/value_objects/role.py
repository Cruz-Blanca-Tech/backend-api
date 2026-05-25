from enum import StrEnum, auto

class Role(StrEnum):
    ADMIN = auto()
    OPERATIVO = auto()
    VISUALIZADOR = auto()