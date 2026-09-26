# -*- coding: utf-8 -*-
import asyncio
from sqlalchemy import text
from src.core.database import engine

async def check():
    async with engine.begin() as c:
        await c.execute(text("UPDATE historical_documents SET document_type = 'Inscripción Educa ' || year || '-1' WHERE document_type LIKE 'Programa Educa%'"))

asyncio.run(check())
