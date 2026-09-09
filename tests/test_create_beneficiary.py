import sys
import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date

sys.path.insert(0, ".")

from src.contexts.core_beneficiary_management.application.use_cases.create_beneficiary_use_case import CreateBeneficiaryUseCase
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import BeneficiaryCreateRequest
from src.contexts.core_beneficiary_management.presentation.schemas.medical_schemas import MedicalRecordCreateRequest
from src.contexts.core_beneficiary_management.presentation.schemas.education_schemas import EducationRecordCreateRequest
from src.contexts.core_beneficiary_management.presentation.schemas.adult_schemas import AdultCreateRequest
from src.core.validators.exceptions import ConflictException, DomainValidationError


class TestCreateBeneficiaryUseCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_repo = AsyncMock()
        self.use_case = CreateBeneficiaryUseCase(repo=self.mock_repo)

    async def test_create_beneficiary_success(self):
        self.mock_repo.get_by_dni.return_value = None
        self.mock_repo.get_by_id.return_value = None

        request = BeneficiaryCreateRequest(
            dni="78901234",
            first_name="Carlos",
            last_name="Gomez",
            birth_date=date(2015, 6, 15),
            gender="M",
            address="Av. Siempre Viva 123",
            baptized=True,
            medical=MedicalRecordCreateRequest(
                has_been_hospitalized=False,
                vaccines=["COVID-19", "INFLUENZA"]
            ),
            education=EducationRecordCreateRequest(
                school="Colegio San Martin",
                grade="3RO_PRIMARIA"
            ),
            related_adults=[
                AdultCreateRequest(
                    dni="44556677",
                    first_name="Maria",
                    last_name="Gomez",
                    role="MOTHER",
                    phone="987654321",
                    is_emergency_contact=True
                )
            ]
        )

        response = await self.use_case.execute(request)

        self.assertIsNotNone(response.id)
        self.assertEqual(response.dni, "78901234")
        self.assertEqual(response.first_name, "Carlos")
        self.assertEqual(response.last_name, "Gomez")
        self.assertEqual(response.gender, "MALE")
        self.assertIsNotNone(response.medical)
        self.assertIn("COVID-19", response.medical.vaccines)
        self.assertIsNotNone(response.education)
        self.assertEqual(response.education.school, "Colegio San Martin")
        self.assertEqual(len(response.related_adults), 1)
        self.assertEqual(response.related_adults[0].first_name, "Maria")
        self.mock_repo.save.assert_called_once()

    async def test_create_beneficiary_with_explicit_id(self):
        explicit_id = uuid4()
        self.mock_repo.get_by_dni.return_value = None
        self.mock_repo.get_by_id.return_value = None

        request = BeneficiaryCreateRequest(
            dni="88990011",
            first_name="Ana",
            last_name="Perez"
        )

        response = await self.use_case.execute(request, explicit_id=explicit_id)

        self.assertEqual(response.id, explicit_id)
        self.assertEqual(response.dni, "88990011")
        self.assertEqual(response.first_name, "Ana")
        self.mock_repo.save.assert_called_once()

    async def test_create_beneficiary_duplicate_dni_raises_conflict(self):
        self.mock_repo.get_by_dni.return_value = MagicMock()

        request = BeneficiaryCreateRequest(
            dni="78901234",
            first_name="Carlos",
            last_name="Gomez"
        )

        with self.assertRaises(ConflictException) as ctx:
            await self.use_case.execute(request)

        self.assertIn("Ya existe un beneficiario registrado con el DNI", ctx.exception.message)
        self.mock_repo.save.assert_not_called()

    async def test_create_beneficiary_duplicate_id_raises_conflict(self):
        explicit_id = uuid4()
        self.mock_repo.get_by_dni.return_value = None
        self.mock_repo.get_by_id.return_value = MagicMock()

        request = BeneficiaryCreateRequest(
            dni="78901234",
            first_name="Carlos",
            last_name="Gomez"
        )

        with self.assertRaises(ConflictException) as ctx:
            await self.use_case.execute(request, explicit_id=explicit_id)

        self.assertIn("Ya existe un beneficiario registrado con el ID", ctx.exception.message)
        self.mock_repo.save.assert_not_called()

    async def test_create_beneficiary_invalid_dni_raises_validation_error(self):
        self.mock_repo.get_by_dni.return_value = None
        self.mock_repo.get_by_id.return_value = None

        # DNI must be 8 digits
        request = BeneficiaryCreateRequest(
            dni="123", # invalid DNI
            first_name="Carlos",
            last_name="Gomez"
        )

        with self.assertRaises(DomainValidationError):
            await self.use_case.execute(request)

        self.mock_repo.save.assert_not_called()
