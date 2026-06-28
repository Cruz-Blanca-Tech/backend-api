from dataclasses import dataclass

@dataclass(frozen=True) # <-- Esto lo convierte en un Value Object puro
class FileItem:
    file_id: str
    file_name: str