# backend-api — Cruz Blanca (Gestión Documental Inteligente)

Backend FastAPI del sistema de gestión documental de la Asociación Cruz Blanca
(proyecto de tesis). Orquesta un pipeline de intake+OCR → triaje de calidad →
maestro de beneficiarios (MDM), con despliegue en Azure Container Apps.

## Arquitectura (bounded contexts)

| Contexto | Responsabilidad |
|---|---|
| `security_access` | Autenticación OAuth Google (dominio `cruz-blanca.org`) y middleware JWT |
| `document_intake_ocr` | Ingesta de lotes de Drive, OCR (Azure Document Intelligence), dossieres |
| `data_quality_triage` | Reglas de dominio, detección de discrepancias, sugerencias IA y correcciones |
| `core_beneficiary_management` | Maestro de beneficiarios (MDM): identidad, familiares, fichas médica/educativa |
| `reporting_analytics` | Reportes y analítica |

Flujo por actividad (p. ej. "Inscripción EDUCA 2026-I"):

```
Lote (Drive) → OCR → Dossier expediente → Triage (reglas + fuzzy + IA)
            → Corrección (WARNING / sugerencia IA) → Aprobación → MDM
```

### Triage y robustez de identidad

- **Reglas de dominio** (`data_quality_triage/domain/educa/rules`): coherencia
  de género (tolera `M`/`F` y el enum del maestro `MALE`/`FEMALE`), edad,
  DNI/agrupación, deduplicación de adultos por DNI, etc.
- **Matcher fuzzy** (`application/shared/services/beneficiary_fuzzy_matcher.py`):
  sugiere "Quizá este beneficiario es → …" solo cuando **DNI y/o nombre difieren**
  del expediente (si coinciden es match MDM, no sugerencia). Scoring compuesto
  (nombres, apellidos, DNI), búsqueda SQL con `translate()` para acentos y
  deduplicación por DNI.
- **Correcciones** (`application/shared/use_cases/submit_correction_use_case.py`):
  al aprobar, normaliza género (`MALE`→`M`, `FEMALE`→`F`) y dispara
  eventos `DossierApprovedEvent`.
- **Sincronización MDM** (`core_beneficiary_management/.../educa_dossier_mapper.py`):
  - ALTA: crea beneficiario + familiares (dedup por DNI, flags de apoderado/emergencia).
  - Beneficiario YA registrado: se preservan identidad y familiares del maestro;
    solo se añaden **tutores nuevos** (nunca padre/madre, y sin duplicar por DNI
    o nombre similar) y se sincronizan los flags `is_guardian` /
    `is_emergency_contact` con `guardian_dni`/`emergency_contact_dni` del expediente.

## Puesta en marcha local

Requisitos: **Python 3.11+**, PostgreSQL (o DATABASE_URL remota), y un `.env`
basado en [.env.example](.env.example) (Azure Document Intelligence y OAuth
Google solo se necesitan para el pipeline completo).

```bash
python -m venv .venv
.\.venv\Scripts\activate          # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # ajustar credenciales
alembic upgrade head              # migraciones
uvicorn src.main:app --reload --port 8000
```

Swagger en `http://localhost:8000/docs`.

## Tests

```bash
pytest -q          # suite completa (pytest.ini → testpaths=tests)
```

La suite cubre reglas de dominio, el matcher fuzzy, el mapper
`EducaDossierMapper` (dedupe, append de tutores, flags MDM), normalización de
género y los casos de uso de intake/triage/MDM. Los scripts one-off de
desarrollo viven en `scratch/` y **no** se recogen (ver `pytest.ini`).

## Despliegue y automatización

- **CI** (`.github/workflows/ca-cruzblanca-backend-*.yml`): job `test` (pytest)
  + job `build-and-deploy` (Azure Container Apps, `cruzblanca2026.azurecr.io`).
- **Flujo de ramas**: `feat/*` → PR a `develop` → PR a `main`; el push a `main`
  dispara el deploy automático. Verificar estado en *Actions* del repo.

Nota: no se suben a git los `.env`, `*.db` locales ni los scripts de `scratch/`.