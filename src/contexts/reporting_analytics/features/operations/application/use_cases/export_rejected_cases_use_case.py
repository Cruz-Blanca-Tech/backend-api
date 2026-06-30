import csv
import io
from typing import AsyncGenerator
from src.contexts.reporting_analytics.features.operations.infrastructure.repositories.sql_operations_repository import SqlOperationsRepository

class ExportRejectedCasesUseCase:
    def __init__(self, repository: SqlOperationsRepository):
        self.repository = repository

    async def execute(self) -> AsyncGenerator[str, None]:
        def dict_to_csv_row(data_dict: dict, fieldnames: list) -> str:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
            writer.writerow(data_dict)
            return output.getvalue()
        
        fieldnames = ["id", "dni_reference", "created_at", "rejection_reason"]
        
        header = io.StringIO()
        writer = csv.DictWriter(header, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        yield header.getvalue()
        
        data = await self.repository.get_rejected_cases_export()
        
        for row in data:
            cleaned_row = {k: ("" if v is None else v) for k, v in row.items()}
            yield dict_to_csv_row(cleaned_row, fieldnames)
