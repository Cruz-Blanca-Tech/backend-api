# src/contexts/document_intake_ocr/domain/services/document_grouper_service.py
from typing import List, Dict
from src.contexts.document_intake_ocr.domain.value_objects.raw_file import RawFile
from src.contexts.document_intake_ocr.domain.value_objects.dossier_proposal import DossierProposal

class DocumentGrouperService:
    @staticmethod
    def group_valid_files(clean_files: List[RawFile]) -> List[DossierProposal]:
        """Agrupa por clave de agrupación (el token antes del primer `_`).

        La clave se usa tal cual, sin normalizar a DNI: un token de 7 u 9
        dígitos agrupa igual que uno de 8, y el expediente resultante lleva esa
        clave anotada para que el revisor vea en triaje que el identificador
        del lote no es un DNI. Ver `GroupKey`.
        """
        grouping: Dict[str, List[RawFile]] = {}

        for file in clean_files:
            # El filtro ya garantiza que `group_key` no es None (si lo fuera,
            # el archivo no habría llegado hasta acá).
            key = file.group_key
            grouping.setdefault(key.value, []).append(file)

        return [
            DossierProposal(
                key=file_list[0].group_key,
                files=file_list,
            )
            for file_list in grouping.values()
        ]
