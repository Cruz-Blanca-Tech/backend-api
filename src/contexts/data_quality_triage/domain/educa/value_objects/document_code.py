from enum import Enum

class EducaDocumentCode(str, Enum):
    FINS = "FINS"
    DJ = "DJ"
    DNI_BENEFICIARY = "DNIBE"
    DNI_APODERADO = "DNIAP"
    DNI_GENERIC = "DNI"
