from pydantic import BaseModel, Field

class FileItemSchema(BaseModel):
    source_uri: str = Field(..., description="Enlace temporal o ruta universal para descargar el archivo")
    file_name: str = Field(..., description="El nombre completo del archivo, ej: 71223344_FINS.pdf")
