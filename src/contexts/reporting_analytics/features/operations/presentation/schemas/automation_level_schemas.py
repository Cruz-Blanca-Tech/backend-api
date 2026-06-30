from pydantic import BaseModel

class AutomationLevelData(BaseModel):
    verdict: str
    count: int
