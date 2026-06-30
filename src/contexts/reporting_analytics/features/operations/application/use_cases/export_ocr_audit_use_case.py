import csv
import io
from typing import AsyncGenerator
from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository

class ExportOcrAuditUseCase:
    def __init__(self, repository: SqlOperationsRepository):
        self.repository = repository

    async def execute(self) -> AsyncGenerator[str, None]:
        def dict_to_csv_row(data_dict: dict, fieldnames: list) -> str:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
            writer.writerow(data_dict)
            return output.getvalue()
        
        fieldnames = [
            "id", "batch_id", "dni_reference", "status", "status_description",
            "verdict", "confidence_scores", "resolved_by", 
            "resolved_at", "created_at"
        ]
        
        STATUS_LEGEND = {
            "APPROVED": "El expediente pasó todas las validaciones de calidad y fue inscrito exitosamente.",
            "REJECTED": "El expediente falló validaciones del OCR o reglas de negocio (ej. firma borrosa).",
            "PENDING": "El expediente está en cola esperando ser procesado por la Inteligencia Artificial."
        }
        
        header = io.StringIO()
        writer = csv.DictWriter(header, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        yield header.getvalue()
        
        data = await self.repository.get_ocr_audit_export()
        
        for row in data:
            # Flatten or stringify complex JSON dicts if needed
            cleaned_row = {}
            for k, v in row.items():
                if v is None:
                    cleaned_row[k] = ""
                elif isinstance(v, dict) or isinstance(v, list):
                    cleaned_row[k] = str(v)
                else:
                    cleaned_row[k] = v
            
            # Map the legend to the new column
            current_status = str(row.get("status", "")).strip()
            cleaned_row["status_description"] = STATUS_LEGEND.get(current_status, "")
                    
            yield dict_to_csv_row(cleaned_row, fieldnames)
