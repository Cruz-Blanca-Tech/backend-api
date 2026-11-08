"""D5: si el OCR no lee la casilla, sabe leer / sabe escribir deben quedar vacios (None),
no en «si» por defecto."""
from src.contexts.data_quality_triage.application.educa.schemas.education_schemas import EducationSchema
from src.contexts.data_quality_triage.domain.educa.value_objects.education_data import EducationData


def test_value_object_sin_valor_por_defecto():
    e = EducationData()
    assert e.knows_read is None
    assert e.knows_write is None


def test_schema_sin_valor_por_defecto():
    e = EducationSchema()
    assert e.knows_read is None
    assert e.knows_write is None


def test_schema_alias_none_no_se_convierte_en_si():
    e = EducationSchema.model_validate({"knows_how_to_read": None, "knows_how_to_write": None})
    assert e.knows_read is None
    assert e.knows_write is None


def test_schema_respeta_valores_leidos():
    e = EducationSchema.model_validate({"knows_how_to_read": False, "knows_how_to_write": True})
    assert e.knows_read is False
    assert e.knows_write is True


def test_regla_exige_elegir_cuando_no_hay_dato():
    from types import SimpleNamespace
    from src.contexts.data_quality_triage.domain.educa.rules.domain.education_rules import EducationRules

    def issues(read, write):
        edu = SimpleNamespace(school="Colegio X", grade="3RO_PRIMARIA", knows_read=read, knows_write=write)
        return {i.field_name for i in EducationRules().evaluate(SimpleNamespace(education=edu)) if i.severity == "ERROR"}

    assert issues(None, None) == {"education.knows_read", "education.knows_write"}
    assert issues(True, None) == {"education.knows_write"}
    assert issues(False, True) == set()
