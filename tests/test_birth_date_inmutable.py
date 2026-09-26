"""La fecha de nacimiento es DATO DEL MAESTRO: se carga una vez (alta) y después
es INMUTABLE (no editable, no actualizable) — tampoco desde el triaje.

Invariante: una vez que `persons.birth_date` tiene valor, ningún camino lo cambia.
Se defiende en tres capas, y cada capa tiene su test:

1. CONTRATO — `BeneficiaryPatchRequest` no expone `birth_date` (no se puede pedir
   un cambio por la API del MDM). El alta (`BeneficiaryCreateRequest`) sí lo lleva:
   es el único momento en que se escribe.
2. PERSISTENCIA — `SqlBeneficiaryRepository.save()` restaura la fecha almacenada
   aunque la entidad llegue con otra. Es el punto único por el que pasan TODOS los
   caminos (PATCH del MDM, aprobación de triaje, ...), así que ningún llamador
   externo puede saltarse la regla.
3. APROBACIÓN DE TRIAJE — `EducaDossierMapper` no toca la fecha de un beneficiario
   ya registrado, salvo para COMPLETARLA si el maestro aún no tiene (si no, un
   beneficiario sin fecha quedaría con el ERROR de completitud y sin forma de
   resolverse desde el triaje).
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

    def __init__(self, stored_birth_date):
        self._stored = stored_birth_date
        self.merged = None

    @property
    def no_autoflush(self):
        return nullcontext()

    async def scalar(self, stmt):
        return self._stored

    async def merge(self, model):
        self.merged = model
        return model

    async def commit(self):
        pass


class TestBirthDateContract(unittest.TestCase):
    """Capa 1 — contrato de la API."""

    def test_el_patch_no_acepta_fecha_de_nacimiento(self):
        self.assertNotIn("birth_date", BeneficiaryPatchRequest.model_fields)

    def test_un_patch_con_fecha_se_ignora(self):
        # Pydantic descarta campos desconocidos: mandarlo no cambia nada.
        patch = BeneficiaryPatchRequest(first_name="Otro", birth_date="1999-09-09")
        self.assertEqual(patch.model_dump(exclude_unset=True), {"first_name": "Otro"})

    def test_el_alta_si_acepta_fecha_de_nacimiento(self):
        # El alta es la única vía de carga: sin esto no existiría fecha nunca.
        self.assertIn("birth_date", BeneficiaryCreateRequest.model_fields)
        alta = BeneficiaryCreateRequest(
            dni="12345678", first_name="Juan", last_name="Perez",
            birth_date="2015-06-15",
        )
        self.assertEqual(alta.birth_date, FECHA_MAESTRO)


class TestBirthDateMapper(unittest.TestCase):
    """Capa 3 — la aprobación de triaje no actualiza la fecha del maestro."""

    def test_existente_con_fecha_no_se_toca(self):
        b = _beneficiary(FECHA_MAESTRO)
        out = EducaDossierMapper.map_to_entity(_dto("2016-01-01"), existing_beneficiary=b)
        self.assertEqual(out.birth_date, FECHA_MAESTRO)

    def test_existente_sin_fecha_se_completa_con_la_de_la_ficha(self):
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


class TestBirthDateRepository(unittest.IsolatedAsyncioTestCase):
    """Capa 2 — el invariante se sostiene pase lo que pase con la entidad."""

    async def test_restaura_la_fecha_almacenada(self):
        session = _FakeSession(FECHA_MAESTRO)
        repo = SqlBeneficiaryRepository(session)
        b = _beneficiary(FECHA_FICHA)  # la entidad llega con otra fecha

        await repo.save(b)

        self.assertEqual(session.merged.birth_date, FECHA_MAESTRO)
        self.assertEqual(b.birth_date, FECHA_MAESTRO)

    async def test_no_toca_una_fecha_inexistente(self):
        # Sin fecha en el maestro: la entidad manda (alta / relleno).
        session = _FakeSession(None)
        repo = SqlBeneficiaryRepository(session)
        b = _beneficiary(FECHA_FICHA)

        await repo.save(b)

        self.assertEqual(session.merged.birth_date, FECHA_FICHA)

    async def test_no_inventa_fecha_si_no_hay_ninguna(self):
        session = _FakeSession(None)
        repo = SqlBeneficiaryRepository(session)
        b = _beneficiary(None)

        await repo.save(b)

        self.assertIsNone(session.merged.birth_date)


if __name__ == "__main__":
    unittest.main()
