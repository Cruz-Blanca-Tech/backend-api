import csv
import io
from typing import AsyncGenerator
from src.contexts.reporting_analytics.features.demographics.infrastructure.repositories.sql_demographics_repository import SqlDemographicsRepository

class ExportBeneficiariesCsvUseCase:
    def __init__(self, repository: SqlDemographicsRepository):
        self.repository = repository

    async def execute(self) -> AsyncGenerator[str, None]:
        # Helper to convert dict to CSV string
        def dict_to_csv_row(data_dict: dict, fieldnames: list) -> str:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
            writer.writerow(data_dict)
            return output.getvalue()
        
        fieldnames = ["id", "name", "gender", "age", "school", "has_document"]
        
        # Yield Header
        header = io.StringIO()
        writer = csv.DictWriter(header, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        yield header.getvalue()
        
        # Get data
        data = await self.repository.get_beneficiaries_master_export()
        
        # Yield rows
        for row in data:
            # Simple conversion for None values to empty strings
            cleaned_row = {k: ("" if v is None else v) for k, v in row.items()}
            yield dict_to_csv_row(cleaned_row, fieldnames)
