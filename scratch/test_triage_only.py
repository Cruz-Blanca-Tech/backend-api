import asyncio
import os
from src.core.database import async_session_maker
from sqlalchemy import text
from src.contexts.shared.events.documents_extracted_event import DocumentsExtractedEvent

# Import ALL models so SQLAlchemy relationships are fully initialized
import src.contexts.document_intake_ocr.infrastructure.persistence.model.extraction_batch_model
import src.contexts.document_intake_ocr.infrastructure.persistence.model.document_item_model
import src.contexts.document_intake_ocr.infrastructure.persistence.model.activity_model
import src.contexts.document_intake_ocr.infrastructure.persistence.model.program_model
from src.contexts.data_quality_triage.application.shared.handlers.triage_event_handler import handle_documents_extracted

async def main():
    # El batch_id y DNI correctos de los logs
    event = DocumentsExtractedEvent(
        batch_id="8f773541-b142-430e-92ee-6270223039b2",
        activity_type="EDUCA_INSCRIPTION",
        dni_reference="90928086"
    )
    print("Disparando evento de triage para 90928086...")
    await handle_documents_extracted(event)
    print("Evento procesado.")
    
    # Comprobar resultado
    async with async_session_maker() as session:
        res = await session.execute(text("SELECT updated_at, discrepancies FROM triage_cases WHERE dni_reference = '90928086'"))
        row = res.fetchone()
        if row:
            import json
            print('Nuevo updated_at:', row[0])
            print('Nuevas discrepancies:', json.dumps(row[1], indent=2))

if __name__ == "__main__":
    asyncio.run(main())
