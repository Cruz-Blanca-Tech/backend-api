from enum import Enum

class RelationshipRole(str, Enum):
    FATHER = "FATHER"
    MOTHER = "MOTHER"
    SIBLING = "SIBLING"
    GRANDPARENT = "GRANDPARENT"
    TUTOR = "TUTOR"
    OTHER = "OTHER"
