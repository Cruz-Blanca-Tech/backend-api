from pydantic import BaseModel

class RegistrationGrowthData(BaseModel):
    month: str
    new_beneficiaries: int
