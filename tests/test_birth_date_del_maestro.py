"""La fecha de nacimiento es DATO DEL MAESTRO (MDM), no del triaje.

Reparto de responsabilidades:
- **El MDM es el dueño.** Si la fecha del maestro está mal, se corrige desde la
  pantalla de beneficiarios (PATCH /beneficiaries). `save()` NO la bloquea: es
  justamente la vía por la que pasa esa corrección.
- **El triaje no la toca.** Al aprobar un expediente de un beneficiario YA
  registrado, `EducaDossierMapper` conserva la fecha del maestro aunque la ficha
  traiga otra — un expediente con la fecha mal leída (OCR) no puede cambiar la
  identidad de la persona.
- **Única excepción, de carga inicial:** si el maestro NO tiene fecha, el
  expediente la completa. Sin eso, un beneficiario registrado sin fecha quedaría
  con el ERROR de completitud (`BeneficiaryCompletenessRule`) sin forma de
  resolverse.
"""
import unittest
import uuid
from contextlib import nullcontext
from datetime import date

import sys
sys.path.insert(0, ".")

from src.contexts.core_beneficiary_management.application.dtos.educa_dossier_dto import (
    EducaBeneficiaryDTO, EducaDossierDTO,
)
from src.contexts.core_beneficiary_management.application.mappers.educa_dossier_mapper import (
    EducaDossierMapper,
)
from src.contexts.core_beneficiary_management.domain.entities.beneficiary import Beneficiary
from src.contexts.core_beneficiary_management.domain.value_objects.dni import DNI
from src.contexts.core_beneficiary_management.infrastructure.persistence.repositories.sql_beneficiary_repository import (
    SqlBeneficiaryRepository,
)
from src.contexts.core_beneficiary_management.presentation.schemas.beneficiary_schemas import (
    BeneficiaryCreateRequest, BeneficiaryPatchRequest,
)

FECHA_MAESTRO = date(2015, 6, 15)
FECHA_FICHA = date(2016, 1, 1)  # la que trae el expediente (distinta, va a perder)
FECHA_CORREGIDA = date(2015, 8, 20)  # la que escribe el revisor en el MDM


def _beneficiary(birth_date):
    return Beneficiary(
        id=uuid.uuid4(),
        dni=DNI("12345678"),
        first_name="Juan",
        last_name="Perez",
        birth_date=birth_date,
    )


def _dto(birth_date=None):
    return EducaDossierDTO(
        beneficiary=EducaBeneficiaryDTO(
            dni="12345678", first_name="Juan", last_name="Perez",
            gender="M", birth_date=birth_date,
        ),
    )


class _FakeSession:
    """Sesión mínima: solo lo que usa `save()` sin familiares."""

    def __init__(self):
        self.merged = None

    @property
    def no_autoflush(self):
        return nullcontext()

    async def scalar(self, statement):
        return None

    async def merge(self, model):
        self.merged = model
        return model

    async def commit(self):
        pass


class TestElMdmEsElDueno(unittest.TestCase):
    """El MDM puede corregir la fecha: es su dueño."""

    def test_el_patch_acepta_corregir_la_fecha(self):
        self.assertIn("birth_date", BeneficiaryPatchRequest.model_fields)
        patch = BeneficiaryPatchRequest(birth_date="2015-08-20")
        self.assertEqual(patch.birth_date, FECHA_CORREGIDA)

    def test_el_alta_acepta_la_fecha(self):
        self.assertIn("birth_date", BeneficiaryCreateRequest.model_fields)

    def test_el_patch_no_toca_nada_mas(self):
        # Un PATCH con la fecha sola no arrastra el resto de la identidad.
        patch = BeneficiaryPatchRequest(birth_date="2015-08-20")
        self.assertEqual(set(patch.model_dump(exclude_unset=True)), {"birth_date"})


class TestElTriajeNoTocaLaFecha(unittest.TestCase):
    """La protección real: un expediente nunca pisa la fecha del maestro."""

    def test_existente_con_fecha_no_se_toca(self):
        b = _beneficiary(FECHA_MAESTRO)
        out = EducaDossierMapper.map_to_entity(_dto("2016-01-01"), existing_beneficiary=b)
        self.assertEqual(out.birth_date, FECHA_MAESTRO)

    def test_existente_sin_fecha_se_completa_con_la_de_la_ficha(self):
        # Carga inicial, no corrección: sin esto el caso quedaría inaprobable.
        b = _beneficiary(None)
        out = EducaDossierMapper.map_to_entity(_dto("2016-01-01"), existing_beneficiary=b)
        self.assertEqual(out.birth_date, FECHA_FICHA)

    def test_existente_sin_fecha_y_ficha_sin_fecha_no_inventa(self):
        b = _beneficiary(None)
        out = EducaDossierMapper.map_to_entity(_dto(None), existing_beneficiary=b)
        self.assertIsNone(out.birth_date)

    def test_alta_toma_la_fecha_de_la_ficha(self):
        out = EducaDossierMapper.map_to_entity(_dto("2016-01-01"), existing_beneficiary=None)
        self.assertEqual(out.birth_date, FECHA_FICHA)


class TestSaveNoBloqueaLaCorreccion(unittest.IsolatedAsyncioTestCase):
    """`save()` es la vía de la corrección del MDM: no debe restaurar la fecha
    almacenada (eso impediría arreglar una fecha mal en el maestro)."""

    async def test_persiste_la_fecha_corregida_del_mdm(self):
        session = _FakeSession()
        repo = SqlBeneficiaryRepository(session)
        b = _beneficiary(FECHA_CORREGIDA)

        await repo.save(b)

        self.assertEqual(session.merged.birth_date, FECHA_CORREGIDA)

    async def test_persiste_la_fecha_del_alta(self):
        session = _FakeSession()
        repo = SqlBeneficiaryRepository(session)
        b = _beneficiary(FECHA_FICHA)

        await repo.save(b)

        self.assertEqual(session.merged.birth_date, FECHA_FICHA)

    async def test_no_inventa_fecha_si_no_hay_ninguna(self):
        session = _FakeSession()
        repo = SqlBeneficiaryRepository(session)
        b = _beneficiary(None)

        await repo.save(b)

        self.assertIsNone(session.merged.birth_date)


if __name__ == "__main__":
    unittest.main()
