from src.core.database import Base
from src.contexts.security_access.infrastructure.persistence.models.refresh_token_model import RefreshTokenModel
import asyncio
import sys
from uuid import UUID
from datetime import datetime
from src.core.database import async_session_maker
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_batch_repository import SqlBatchRepository
from src.contexts.document_intake_ocr.infrastructure.persistence.repositories.sql_activity_repository import SqlActivityRepository
from src.contexts.document_intake_ocr.infrastructure.dependencies.batch_deps import get_storage_adapter, get_single_document_processor, get_dossier_event_publisher
from src.contexts.document_intake_ocr.application.use_cases.reprocess_dossier_use_case import ReprocessDossierUseCase
from sqlalchemy import text

class FakeBackgroundTasks:
    def add_task(self, func, *args, **kwargs):
        # Fire and forget asynchronously just like FastAPI BackgroundTasks
        asyncio.create_task(func(*args, **kwargs))

async def main():
    print("Iniciando prueba E2E...")
    async with async_session_maker() as session:
        batch_repo = SqlBatchRepository(session)
        activity_repo = SqlActivityRepository(session)
        storage = get_storage_adapter()
        
        from src.contexts.document_intake_ocr.infrastructure.adapters.azure_document_extractor import AzureDocumentExtractor
        from src.core.config import settings
        extractor = AzureDocumentExtractor(
            endpoint=settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
            key=settings.AZURE_DOCUMENT_INTELLIGENCE_KEY
        )
        from src.contexts.document_intake_ocr.infrastructure.adapters.llm_data_normalizer import LLMDataNormalizer
        normalizer = LLMDataNormalizer(api_key=settings.AZURE_OPENAI_API_KEY, endpoint=settings.AZURE_OPENAI_ENDPOINT)
        
        from src.contexts.document_intake_ocr.application.services.single_document_processor import SingleDocumentProcessor
        single_doc_processor = SingleDocumentProcessor(storage, extractor, normalizer)
        event_pub = get_dossier_event_publisher()
        
        use_case = ReprocessDossierUseCase(
            batch_repo=batch_repo,
            activity_repo=activity_repo,
            storage_adapter=storage,
            single_doc_processor=single_doc_processor,
            event_publisher=event_pub
        )
        
        # 1. Let's find a valid batch and dni
        res = await session.execute(text("SELECT batch_id, dni_reference FROM document_items LIMIT 1"))
        row = res.fetchone()
        batch_id = row[0]
        dni = row[1]
        
        print(f"Lanzando Use Case para Batch={batch_id}, DNI={dni}")
        
        bg_tasks = FakeBackgroundTasks()
        
        # Ejecutar el caso de uso
        response = await use_case.execute(
            batch_id=batch_id,
            dni_reference=dni,
            user_email="prueba@cruzblanca.org",
            background_tasks=bg_tasks
        )
        print(f"Respuesta del Use Case: {response}")
        
    print("Esperando a que la tarea en background haga su trabajo...")
    start_time = datetime.now()
    
    while True:
        async with async_session_maker() as session:
            res = await session.execute(text(f"SELECT file_name, status, failure_reason FROM document_items WHERE batch_id = '{batch_id}' AND dni_reference = '{dni}'"))
            docs = res.fetchall()
            
            all_done = True
            print(f"\\n--- Estado a los {(datetime.now() - start_time).seconds} segundos ---")
            for name, status, reason in docs:
                print(f"[{status}] {name} {f'({reason})' if reason else ''}")
                if status in ('PENDING', 'PROCESSING'):
                    all_done = False
                    
            if all_done and (datetime.now() - start_time).seconds > 2:
                print("\\n¡PROCESO TERMINADO CON EXITO!")
                break
                
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
