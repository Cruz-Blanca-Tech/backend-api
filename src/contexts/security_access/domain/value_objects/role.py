from enum import StrEnum, auto

class Role(StrEnum):
    ADMIN = auto()
    OPERATIVO = auto()
    REVISOR = auto()
    VISUALIZADOR = auto()