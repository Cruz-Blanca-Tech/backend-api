from pydantic import BaseModel

class SchoolDistributionData(BaseModel):
    school: str
    count: int
