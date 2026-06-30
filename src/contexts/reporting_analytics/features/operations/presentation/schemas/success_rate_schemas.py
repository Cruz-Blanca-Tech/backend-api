from pydantic import BaseModel

class SuccessRateData(BaseModel):
    status: str
    count: int
