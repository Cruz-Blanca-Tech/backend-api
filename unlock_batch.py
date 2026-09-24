import asyncio
from src.core.database import async_session_maker
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        # Revert batch to COMPLETED so UI unlocks
        await session.execute(text("UPDATE extraction_batches SET status = 'COMPLETED' WHERE id = '8f773541-b142-430e-92ee-6270223039b2'"))
        
        # Reset documents to PENDING or READY_FOR_REVIEW
        await session.execute(text("UPDATE document_items SET status = 'READY_FOR_REVIEW' WHERE batch_id = '8f773541-b142-430e-92ee-6270223039b2'"))
        
        await session.commit()
        print("Lote desbloqueado con éxito.")

if __name__ == "__main__":
    asyncio.run(main())
