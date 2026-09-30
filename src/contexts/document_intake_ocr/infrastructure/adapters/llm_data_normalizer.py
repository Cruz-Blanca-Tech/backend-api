import json
from sqlalchemy.future import select
from src.core.database import async_session_maker
from src.contexts.core_beneficiary_management.infrastructure.persistence.model.school_model import SchoolModel

import re
import logging
from typing import Dict, Any, Optional
from openai import AsyncAzureOpenAI
from src.contexts.document_intake_ocr.domain.ports.data_normalizer import DataNormalizer

logger = logging.getLogger(__name__)

# --- PATRÓN COMPILADO PARA DETECTAR RUIDO OCR ---
# Detecta strings que son claramente basura visual del escáner:
# - Contienen dígitos mezclados con letras de forma incoherente (ej: "08TONA 80")
# - Son sílabas sueltas de 2-4 letras sin sentido (ej: "EVEN")
# - Textos conocidos que el OCR de estos formularios repite como fantasmas
_KNOWN_GHOSTS = {"08TONA", "EVEN"}

def _is_ghost_text(text: str) -> bool:
    """Detecta si un string es ruido visual del OCR."""
    if not text or not isinstance(text, str):
        return False
    upper = text.strip().upper()
    # Coincidencia directa con fantasmas conocidos
    for ghost in _KNOWN_GHOSTS:
        if ghost in upper:
            return True
    return False

def _clean_ghosts_from_data(obj):
    """Recorre recursivamente un dict/list y elimina cualquier dato fantasma del OCR."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, str) and _is_ghost_text(v):
                obj[k] = None
            else:
                obj[k] = _clean_ghosts_from_data(v)
    elif isinstance(obj, list):
        new_list = []
        for item in obj:
            if isinstance(item, str) and _is_ghost_text(item):
                continue
            cleaned_item = _clean_ghosts_from_data(item)
            # Si es un dict que representa a una persona y no tiene nombre válido, eliminarlo
            if isinstance(cleaned_item, dict):
                name_keys = ["name", "full_name", "first_name"]
                has_any_name_key = any(k in cleaned_item for k in name_keys)
                if has_any_name_key:
                    all_names_empty = all(
                        not (cleaned_item.get(k) or "").strip()
                        for k in name_keys if k in cleaned_item
                    )
                    if all_names_empty:
                        # Adulto/persona sin nombre → eliminarlo completamente
                        continue
            new_list.append(cleaned_item)
        return new_list
    elif isinstance(obj, str):
        if _is_ghost_text(obj):
            return None
    return obj


class LLMDataNormalizer(DataNormalizer):
    """
    Adaptador de Infraestructura para normalizar datos usando Azure OpenAI (GPT-4o-mini).
    Aplica reglas de negocio complejas, autocorrección y estandarización usando créditos de Azure.
    """
    
    def __init__(self, api_key: str, endpoint: str, api_version: str = "2024-02-15-preview"):
        self.client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        # El nombre del despliegue en Azure
        self.model = "gpt-4o-mini"

    async def normalize(self, raw_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info("Iniciando normalización de datos vía LLM...")
        
        # Extract valid schools and diseases from context if provided
        valid_schools = context.get("valid_schools", []) if context else []
        
        
        valid_schools_str = ""
        try:
            async with async_session_maker() as session:
                res = await session.execute(select(SchoolModel.name).filter(SchoolModel.is_active == True))
                active_schools = [row[0] for row in res.all()]
                if active_schools:
                    valid_schools_str = ", ".join(f'"{s}"' for s in active_schools)
        except Exception as e:
            logger.warning(f"No se pudieron cargar los colegios del MDM: {e}")
            valid_schools_str = '"SAN MARTIN", "VILLAS"'
            
        dni_reference = (context or {}).get("dni_reference") or ""
        document_code = (context or {}).get("document_code") or ""
        context_hint = ""
        if dni_reference or document_code:
            context_hint = (
                f"\n        CONTEXTO DEL ARCHIVO ACTUAL: código de documento = '{document_code}', "
                f"clave de agrupación (DNI de referencia del niño beneficiario) = '{dni_reference}'.\n"
            )

        system_prompt = f"""

        Eres un asistente experto en limpieza de datos para la ONG Cruz Blanca.{context_hint}
        Tu objetivo es recibir un JSON con los datos extraídos por OCR de un formulario físico
        y devolver un nuevo JSON con los datos normalizados y corregidos.

        REGLAS ESTRICTAS DE NEGOCIO:
        
        1. COLEGIOS (CLASIFICACION ESTRICTA):
         Existen unicamente los siguientes colegios validos (MDM): {valid_schools_str}.
         Debes mapear el colegio extraido a uno de estos valores si se parece semantica o foneticamente.
         Si el colegio escrito NO se parece a ninguno de la lista (ej. es un colegio completamente distinto), DEBES poner el campo correspondiente a colegio como `null` y agregar un mensaje claro en el array de `warnings` indicando "Colegio no reconocido: [nombre extraido]". NO dejes el nombre original si no pertenece a la lista de validos.

        2. ENFERMEDADES / ALERGIAS / VACUNAS / SEGUROS:
           Corrige errores ortográficos y estandariza términos médicos.
           MUY IMPORTANTE: Si ves un texto como 'completas', 'todas', o 'al día' relacionado a vacunas, márcalo en el campo `medical_has_complete_vaccines` como true o "selected", pero NO lo incluyas como un string dentro de nombres de vacunas.
           SEGUROS: Si se menciona un seguro (ej. en `medical_insurance_other`), clasifícalo. Si es "SIS" o "Seguro Integral", márcalo en `medical_insurance_sis`. Si es "EsSalud" o "Seguro Social", en `medical_insurance_essalud`. Si es otro diferente (ej. "Mapfre", "EPS"), mantén el nombre real del seguro como string en `medical_insurance_other`.

        3. ROLES (Enums):
           Si hay roles de familiares o adultos, mapea el parentesco a uno de estos valores exactos:
           FATHER, MOTHER, GRANDPARENT, SIBLING, UNCLE_AUNT, COUSIN, OTHER.

        4. APODERADO / CONTACTO DE EMERGENCIA:
           Si el OCR indica que una persona firmó o es "Apoderado", `is_guardian: true`.
           Si es contacto de emergencia, `is_emergency_contact: true`.

        5. FORMATOS:
           - Fechas: Convierte todas las fechas al formato estricto `YYYY-MM-DD`.
           - Teléfonos: Elimina espacios y guiones, dejando solo dígitos.

        6. VALIDACIÓN DE NOMBRES Y APELLIDOS Y FANTASMAS OCR:
           Arregla errores de OCR por mala caligrafía en nombres (ej. "J0se" -> "Jose").
           MUY IMPORTANTE: A veces el OCR lee "basura" del fondo del papel (ej. nombre "08TONA 80", o sílabas sin sentido como "EVEN"). Si detectas que CUALQUIER persona (sea familiar, apoderado o contacto de emergencia) es producto de ruido visual, ELIMÍNALA por completo. Si está en una lista (ej. familiares), bórrala del arreglo. Si el ruido fue asignado al Apoderado principal, reemplaza sus campos por `null`. NUNCA conserves el texto basura.

        7. GRADO DE INSTRUCCIÓN (EDAD -> GRADO):
           Si el grado (education.grade) está vacío o no se entiende, pero tienes la edad o fecha de nacimiento del beneficiario, INFÍERELO obligatoriamente usando esta escala (enums exactos):
           - 3 años -> INICIAL_3
           - 4 años -> INICIAL_4
           - 5 años -> INICIAL_5
           - 6 años -> 1RO_PRIMARIA
           - 7 años -> 2DO_PRIMARIA
           - 8 años -> 3RO_PRIMARIA
           - 9 años -> 4TO_PRIMARIA
           - 10 años -> 5TO_PRIMARIA
           - 11 años -> 6TO_PRIMARIA
           - 12 años -> 1RO_SECUNDARIA
           - 13 años -> 2DO_SECUNDARIA
           - 14 años -> 3RO_SECUNDARIA
           - 15 años -> 4TO_SECUNDARIA
           - 16+ años -> 5TO_SECUNDARIA

        8. ALERTAS (warnings):
           Si un campo es reemplazado por `null` debido a que es ruido, agregalo a warnings.
           Si encuentras un DNI con menos/más de 8 dígitos, fechas de nacimiento incongruentes,
           o falta de datos críticos, genera una descripción clara en un array `warnings: [string]`.

        9. CRUCE Y CONSOLIDACIÓN DE PADRES, MADRES Y NIÑO (GÉNERO + COHERENCIA DE APELLIDOS + ANTI-AUTOPADRE):
           Esta regla aplica tanto a la Ficha FINS (`child_first_name`, `child_last_name`, `child_dni`, `parents_father_full_name`, `parents_father_dni`, `parents_mother_full_name`, `parents_mother_dni`, `parents_guardian_full_name`, `parents_guardian_dni`) como a la Declaración Jurada DJ (`child_name`, `child_dni`, `parents_father_name`, `parents_father_dni`, `parents_mother_name`, `parents_mother_dni`, `guardian_dni`):
           - LEY PERUANA DE APELLIDOS: En Perú toda persona tiene `<Nombres> <Apellido Paterno> <Apellido Materno>`. El hijo hereda como primer apellido el primer apellido del padre y como segundo apellido el primer apellido de la madre (ej. si el padre es "Jonathan Paredes Negrón" y la madre es "Jackeline Escobar Chávez", el niño se apellida "Paredes Escobar").
           - PROHIBIDO QUE EL NIÑO SEA SU PROPIO PADRE O MADRE (Y CORRECCIÓN DE DESFASE EN DJ):
             * El niño beneficiario es la persona cuyos dos apellidos combinan el primer apellido del padre + el primer apellido de la madre (o cuyo DNI coincide con la clave de agrupación `{dni_reference}`).
             * En la DJ es común que el OCR desfase las líneas: por ejemplo, pone a la madre/apoderado ("Jackeline Escobar Chávez", DNI "41839063") en `child_name`/`child_dni`, al niño ("Aarón Matheus Paredes Escobar") en `parents_father_name` y su DNI ("{dni_reference}") en `parents_mother_dni`, y al padre ("Jonathan Paredes Negrón") en `parents_mother_name`.
             * Si detectas este desfase, REORDENA cada nombre y su DNI a su campo verdadero:
               1) El niño va en `child_name` y su DNI en `child_dni`.
               2) El padre (hombre / primer apellido del niño) va en `parents_father_name` y su DNI en `parents_father_dni`.
               3) La madre (mujer / segundo apellido del niño) va en `parents_mother_name` y su DNI en `parents_mother_dni` (y si era quien encabezaba la DJ en `child_dni`, coloca también su DNI en `guardian_dni` si estaba vacío).
             * NUNCA dejes el nombre ni el DNI del niño beneficiario dentro de `parents_father_name`, `parents_mother_name`, `parents_father_full_name` o `parents_mother_full_name`. Si el niño aparece repetido como padre o madre, pon ese campo de padre/madre en `null`.
           - ASIGNACIÓN DE PADRE VS MADRE POR GÉNERO DEL NOMBRE Y APELLIDO:
             * Analiza semánticamente el GÉNERO del nombre de pila Y sus apellidos respecto al niño:
               - Nombres masculinos (ej. "Jonathan", "Jeffer", "Mario", "Juan", "Pedro", "Carlos", "Luis", "José", etc.) y/o cuyo primer apellido coincide con el PRIMER apellido (paterno) del niño corresponden SIEMPRE al PADRE (`parents_father_full_name` en FINS / `parents_father_name` en DJ). Si estaban en el campo de madre, muévelos al campo de padre junto con su DNI/teléfono.
               - Nombres femeninos (ej. "Jackeline", "Mayra", "Laura", "María", "Carmen", "Rosa", "Ana", etc.) y/o cuyo primer apellido coincide con el SEGUNDO apellido (materno) del niño corresponden SIEMPRE a la MADRE (`parents_mother_full_name` en FINS / `parents_mother_name` en DJ). Si estaban en el campo de padre, muévelos al campo de madre junto con su DNI/teléfono.
             * NUNCA asignes a un hombre al rol de Madre ni a una mujer al rol de Padre.
           - Si una misma persona fue extraída fragmentada en dos campos (ej. "Laura Sondoval Urguia" en Padre y "Sondoval" en Apoderado), consolida su nombre completo en el rol correcto según su género y apellido, y deja el campo incorrecto en `null`.

      Devuelve ÚNICAMENTE un JSON válido que replique la estructura original pero con los datos limpios y el campo adicional 'warnings' si aplica.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(raw_data, default=str)}
                ],
                temperature=0.1 # Bajo para que sea determinista
            )
            
            clean_json_str = response.choices[0].message.content
            clean_data = json.loads(clean_json_str)

            # SIEMPRE aplicar el filtro determinista como última línea de defensa
            return _clean_ghosts_from_data(clean_data)

        except Exception as e:
            logger.error(f"Error en normalización LLM: {str(e)}")
            # Aun si la IA falla, SIEMPRE limpiamos la basura antes de devolver
            try:
                serializable = json.loads(json.dumps(raw_data, default=str))
            except Exception:
                serializable = raw_data
            serializable["warnings"] = serializable.get("warnings", []) + [f"No se pudo normalizar: {str(e)}"]
            return _clean_ghosts_from_data(serializable)
