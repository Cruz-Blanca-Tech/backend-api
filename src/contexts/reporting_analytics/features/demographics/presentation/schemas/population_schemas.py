from pydantic import BaseModel

class PopulationPyramidData(BaseModel):
    age_group: str
    male: int
    female: int
