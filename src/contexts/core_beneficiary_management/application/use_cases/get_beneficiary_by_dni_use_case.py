from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import SqlBeneficiaryRepository
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import MdmBeneficiaryMatchResponse
from src.contexts.core_beneficiary_management.presentation.mappers.beneficiary_dto_mapper import BeneficiaryDtoMapper


class GetBeneficiaryByDniUseCase:
    """Busca un beneficiario por DNI en el dato máster para el triaje.

    Si existe, devuelve un snapshot LIGERO de identidad + familiares (datos del
    maestro = la verdad). Si no, `exists=False` — la pantalla de corrección sigue
    con el flujo de alta normal (beneficiario nuevo).
    """

    def __init__(self, repo: SqlBeneficiaryRepository):
        self.repo = repo

    async def execute(self, dni: str) -> MdmBeneficiaryMatchResponse:
        beneficiary = await self.repo.get_by_dni(dni)
        if not beneficiary:
            return MdmBeneficiaryMatchResponse(exists=False, beneficiary=None)
        snapshot = BeneficiaryDtoMapper.to_mdm_snapshot(beneficiary)
        return MdmBeneficiaryMatchResponse(exists=True, beneficiary=snapshot)