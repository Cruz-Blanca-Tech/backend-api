import asyncio
import sys
from uuid import UUID
from src.core.database import async_session_maker
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import SqlBatchRepository

async def main():
    async with async_session_maker() as session:
        batch_repo = SqlBatchRepository(session)
        
        from sqlalchemy import text
        res = await session.execute(text("SELECT id FROM extraction_batches LIMIT 1"))
        batch_id = res.scalar()
        if not batch_id: return
            
        res = await session.execute(text(f"SELECT dni_reference FROM document_items WHERE batch_id = '{batch_id}' LIMIT 1"))
        dni = res.scalar()
        
        batch = await batch_repo.get_by_id(batch_id)
        dossiers = batch.dossiers
        rejected = batch.rejected_documents
        print(f"Dossiers found: {len(dossiers)}")
        for d in dossiers:
            if str(d.dni) == dni:
                print(f" - DNI MATCH: {d.dni}, Docs: {len(d.documents)}")
                for doc in d.documents:
                    print(f"   -> {doc.file_name} (Status: {doc.status}, config: {doc.document_type_config_id})")
        
        target_dossier = next((d for d in batch.dossiers if str(d.dni) == dni), None)
        rejected_matches = [doc for doc in batch.rejected_documents if str(doc.dni_reference) == dni]
        
        print(f"target_dossier found? {bool(target_dossier)}")
        print(f"rejected_matches count: {len(rejected_matches)}")
        
if __name__ == "__main__":
    asyncio.run(main())
