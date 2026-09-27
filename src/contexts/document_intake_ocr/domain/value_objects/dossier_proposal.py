# src/contexts/document_intake_ocr/domain/value_objects/dossier_proposal.py
from dataclasses import dataclass
from typing import List
from src.contexts.document_intake_ocr.domain.value_objects.group_key import GroupKey
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile

@dataclass(frozen=True)
class DossierProposal:
    key: GroupKey
    files: List[RawFile]

    def with_files(self, new_files: List[RawFile]) -> 'DossierProposal':
        """
        Retorna una NUEVA instancia inmutable de la propuesta, 
        manteniendo la clave pero actualizando la lista de archivos.
        """
        return DossierProposal(key=self.key, files=new_files)
