# src/contexts/document_intake_ocr/domain/value_objects/dossier_proposal.py
from dataclasses import dataclass
from typing import List
from src.contexts.document_intake_ocr.domain.value_objects.dni import DNI
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile

@dataclass(frozen=True)
class DossierProposal:
    dni: DNI
    files: List[RawFile]

    def with_files(self, new_files: List[RawFile]) -> 'DossierProposal':
        """
        Retorna una NUEVA instancia inmutable de la propuesta, 
        manteniendo el DNI pero actualizando la lista de archivos.
        """
        return DossierProposal(dni=self.dni, files=new_files)