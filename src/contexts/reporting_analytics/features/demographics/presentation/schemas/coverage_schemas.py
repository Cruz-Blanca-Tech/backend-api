from pydantic import BaseModel

class DocumentCoverageData(BaseModel):
    name: str
    value: int
