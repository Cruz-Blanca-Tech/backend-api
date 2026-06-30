from pydantic import BaseModel

class DailyVolumeData(BaseModel):
    day: str
    total_cases: int
