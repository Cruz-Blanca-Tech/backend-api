# src/contexts/document_intake_ocr/domain/services/document_grouper_service.py
from typing import List, Dict
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile
from src.contexts.document_intake_ocr.domain.value_objects.dossier_proposal import DossierProposal

class DocumentGrouperService:
    @staticmethod
    def group_valid_files(clean_files: List[RawFile]) -> List[DossierProposal]:
        """
        Agrupa archivos que ya pasaron los filtros de calidad.
        """
        # TIPADO EXPLÍCITO: Le decimos al editor que las llaves son strings 
        # y los valores son listas de RawFile
        grouping: Dict[str, List[RawFile]] = {}
        
        for file in clean_files:
            # El editor ya sabe que 'file' es RawFile gracias a los parámetros de la función
            dni_str = str(file.extracted_dni.value) 
            grouping.setdefault(dni_str, []).append(file)

        return [
            # Ahora el editor sabe que 'file_list' es List[RawFile], 
            # por lo que file_list[0] iluminará correctamente 'extracted_dni'
            DossierProposal(dni=file_list[0].extracted_dni, files=file_list) 
            for file_list in grouping.values()
        ]