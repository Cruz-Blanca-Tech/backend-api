"""D17 (HU-004/HU-005): al consolidar en el MDM, el nombre completo del adulto
no debe cortarse en el primer espacio: «Juan Carlos Pérez Gómez» debe quedar
como nombre «Juan Carlos» y apellidos «Pérez Gómez».

Se ejercita `EducaDossierMapper.map_to_entity` (mapper real del MDM) con un
expediente aprobado ficticio. Contraste: «Rosa Pérez Gómez» → «Rosa» / «Pérez Gómez».
"""
import pytest

from src.contexts.core_beneficiary_management.application.dtos.educa_dossier_dto import EducaDossierDTO
from src.contexts.core_beneficiary_management.application.mappers.educa_dossier_mapper import EducaDossierMapper


def _adulto(full_name):
    dto = EducaDossierDTO.model_validate({
        "beneficiary": {"dni": "12345678", "first_name": "LUIS", "last_name": "PEREZ ROJAS"},
        "related_adults": {
            "adults": [{"dni": "40000001", "full_name": full_name, "relationship": "FATHER", "phone": "987654321"}],
            "guardian_dni": "40000001", "emergency_contact_dni": "40000001",
        },
    })
    entity = EducaDossierMapper.map_to_entity(dto)
    adultos = list(entity.relatives)
    assert adultos, f"Precondición: el mapper debía crear el adulto; entidad: {entity!r}"
    a = adultos[0]
    return a.first_name, a.last_name


class TestD17NombreAdultoMdm:
    def test_nombre_compuesto_y_dos_apellidos(self):
        obtenido = _adulto("Juan Carlos Pérez Gómez")
        assert obtenido == ("Juan Carlos", "Pérez Gómez"), (
            f"HALLAZGO (D17): «Juan Carlos Pérez Gómez» llega al maestro como nombre/apellidos {obtenido}."
        )

    def test_nombre_compuesto_y_un_apellido(self):
        # Caso con el que el registro describe D17: «Juan Carlos Pérez» -> «Juan» / «Carlos Pérez».
        obtenido = _adulto("Juan Carlos Pérez")
        assert obtenido == ("Juan Carlos", "Pérez"), (
            f"HALLAZGO (D17): «Juan Carlos Pérez» (un solo apellido) llega al maestro como nombre/apellidos {obtenido}."
        )

    def test_apellido_con_particula(self):
        obtenido = _adulto("Pedro de la Cruz Huamán")
        assert obtenido == ("Pedro", "de la Cruz Huamán"), (
            f"HALLAZGO (D17): «Pedro de la Cruz Huamán» (apellido con partícula) llega al maestro como "
            f"nombre/apellidos {obtenido}."
        )

    def test_contraste_un_nombre_y_dos_apellidos(self):
        assert _adulto("Rosa Pérez Gómez") == ("Rosa", "Pérez Gómez")


# ---------------------------------------------------------------------------
# Casos agregados en la corrección v2 (fix/d17-nombre-adulto-v2). Datos ficticios.
# Opción B2: los apellidos del adulto se anclan en los del menor (coincidencia
# exacta por unidad, sin tildes ni mayúsculas; las partículas van dentro de la
# unidad). Máximo 2 unidades de apellido. La coincidencia en la ÚLTIMA unidad
# solo vale para padre/madre (parentesco FATHER/MOTHER). Sin coincidencia, o sin
# apellidos del menor, se usa la regla anterior (dos últimas unidades).
# ---------------------------------------------------------------------------
from types import SimpleNamespace

from src.contexts.core_beneficiary_management.application.dtos.educa_dossier_dto import EducaAdultDTO
from src.contexts.core_beneficiary_management.application.mappers.educa_dossier_mapper import _build_adult


def _adulto_con(full_name, relationship, apellidos_menor, contacto=False):
    dto = EducaDossierDTO.model_validate({
        "beneficiary": {"dni": "12345678", "first_name": "LUIS", "last_name": apellidos_menor},
        "related_adults": {
            "adults": [
                {"dni": "40000001", "full_name": "Carlos Rojas Pérez", "relationship": "FATHER", "phone": "987654321"},
                {"dni": "40000002", "full_name": full_name, "relationship": relationship, "phone": "987654322"},
            ],
            "guardian_dni": "40000001",
            "emergency_contact_dni": "40000002" if contacto else "40000001",
        },
    })
    entity = EducaDossierMapper.map_to_entity(dto)
    a = next(r for r in entity.relatives if r.dni.value == "40000002")
    if contacto:
        assert a.is_emergency_contact, "Precondición: el adulto debía ser el contacto de emergencia"
    return a.first_name, a.last_name


class TestD17AnclaEnApellidosDelMenor:
    def test_madre_dos_nombres_y_dos_apellidos(self):
        assert _adulto_con("Ana María Rojas Díaz", "MOTHER", "PEREZ ROJAS") == ("Ana María", "Rojas Díaz")

    def test_madre_dos_nombres_y_un_apellido(self):
        assert _adulto_con("Ana María Rojas", "MOTHER", "PEREZ ROJAS") == ("Ana María", "Rojas")

    def test_madre_con_nombre_igual_a_apellido_del_menor_tope_de_dos(self):
        # «Cruz» es nombre de la madre y también apellido del menor: el tope de
        # 2 unidades de apellido descarta esa coincidencia y ancla en «Rojas».
        assert _adulto_con("María Cruz Rojas Díaz", "MOTHER", "CRUZ ROJAS") == ("María Cruz", "Rojas Díaz")

    def test_padre_con_particula_coincide_por_unidad(self):
        assert _adulto_con("Pedro de la Cruz Huamán", "FATHER", "DE LA CRUZ ROJAS") == ("Pedro", "de la Cruz Huamán")

    def test_padre_coincidencia_sin_tildes(self):
        assert _adulto_con("José Luis Núñez", "FATHER", "NUNEZ ROJAS") == ("José Luis", "Núñez")

    def test_prima_no_ancla_en_la_ultima_palabra(self):
        # Otro parentesco: «Pérez» (apellido del menor) cae en la última palabra,
        # así que no se usa como ancla y se aplica la regla de respaldo.
        assert _adulto_con("Rosa Huamán Pérez", "OTHER", "PEREZ ROJAS") == ("Rosa", "Huamán Pérez")

    def test_contacto_de_emergencia_sin_apellidos_en_comun(self):
        assert _adulto_con("Carmen Rosa Villanueva Torres", "OTHER", "PEREZ ROJAS", contacto=True) == (
            "Carmen Rosa", "Villanueva Torres"
        )

    @pytest.mark.parametrize("apellidos_menor", ["", "   ", None])
    def test_menor_sin_apellidos_usa_la_regla_de_respaldo(self, apellidos_menor):
        # El DTO del MDM exige apellidos del menor (D22); se ejercita _build_adult
        # directamente. Sin apellidos no hay ancla: mismo resultado que hoy.
        ad = EducaAdultDTO(dni="40000001", full_name="Juan Carlos Pérez", relationship="FATHER")
        dto = SimpleNamespace(
            beneficiary=SimpleNamespace(first_name="LUIS", last_name=apellidos_menor),
            related_adults=SimpleNamespace(emergency_contact_dni=None, guardian_dni=None),
        )
        adult = _build_adult(ad, dto, "40000001")
        assert (adult.first_name, adult.last_name) == ("Juan", "Carlos Pérez")

    def test_coincidencia_que_dejaria_nombres_vacios_usa_el_respaldo(self):
        # «Pérez» coincide con el menor, pero anclar ahí dejaría los nombres vacíos:
        # se usa la regla de respaldo (mismo resultado que hoy), nunca nombres vacíos.
        assert _adulto_con("Pérez Gómez", "FATHER", "PEREZ ROJAS") == ("Pérez", "Gómez")
