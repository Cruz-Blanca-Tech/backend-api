from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class BatchOcrCompletedEvent:
    """
    Evento que se dispara cuando el motor de OCR ha terminado de procesar TODOS 
    los documentos de un lote, y ha enviado los eventos individuales por expediente.
    """
    batch_id: UUID
