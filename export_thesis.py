#!/usr/bin/env python3
"""
Script de exportación para tesis: auditoría completa de expedientes.

Uso:
    python export_thesis.py --batch-id <BATCH_UUID> --output formato [json|excel] --file archivo_salida
    python export_thesis.py --all --output excel --file tesis_data.xlsx

Exporta por expediente:
  - created_at          : cuándo se creó el expediente (1er procesamiento IA)
  - completed_at        : cuándo terminó el procesamiento (auto o manual)
  - errores_iniciales   : errores del primer procesamiento (desde original_dossier_data)
  - errores_finales     : errores al cerrar el expediente
  - correcciones_usuario: cuántas correcciones manuales hizo el usuario (audit_log action=CORRECTED)
  - correcciones_auto   : cuántas correcciones automáticas (audit_log action=AUTO_CORRECTION)
  - usuario_final       : quién aprobó/rechazó (resolved_by)
  - status, verdict     : estado y veredicto final
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import async_session_maker
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_case_model import TriageCaseModel
from src.contexts.data_quality_triage.infrastructure.persistence.model.triage_audit_log_model import TriageAuditLogModel


async def export_thesis_data(
    batch_id: UUID | None = None,
    limit: int | None = None,
    offset: int = 0
) -> list[dict]:
    """Exporta datos de auditoría para tesis."""
    
    async with async_session_maker() as session:
        # Query principal: expedientes con conteos pre-agregados
        # CAST explícito para evitar AmbiguousParameterError con asyncpg
        if batch_id:
            batch_id_sql = f"'{str(batch_id)}'::uuid"
            where_clause = f"WHERE tc.batch_id = '{str(batch_id)}'::uuid"
        else:
            where_clause = ""
        
        query = text(f"""
            SELECT 
                tc.id,
                tc.batch_id,
                tc.dni_reference,
                tc.created_at,
                tc.completed_at,
                tc.resolved_at,
                tc.resolved_by,
                tc.status,
                tc.verdict,
                tc.dossier_data,
                tc.original_dossier_data,
                tc.discrepancies,
                -- Errores iniciales (del primer procesamiento)
                COALESCE((
                    SELECT count(*) 
                    FROM jsonb_array_elements(tc.original_dossier_data->'validation_issues') vi
                    WHERE vi->>'severity' = 'ERROR'
                ), 0) AS errores_iniciales,
                -- Errores finales
                COALESCE((
                    SELECT count(*) 
                    FROM jsonb_array_elements(tc.discrepancies) d
                    WHERE d->>'severity' = 'ERROR'
                ), 0) AS errores_finales,
                -- Warnings finales
                COALESCE((
                    SELECT count(*) 
                    FROM jsonb_array_elements(tc.discrepancies) d
                    WHERE d->>'severity' = 'WARNING'
                ), 0) AS warnings_finales,
                -- AI_INSIGHTs finales
                COALESCE((
                    SELECT count(*) 
                    FROM jsonb_array_elements(tc.discrepancies) d
                    WHERE d->>'severity' = 'AI_INSIGHT'
                ), 0) AS ai_insights_finales,
                -- Correcciones manuales del usuario
                COALESCE((
                    SELECT count(*) 
                    FROM triage_audit_log al 
                    WHERE al.triage_case_id = tc.id AND al.action = 'CORRECTED'
                ), 0) AS correcciones_usuario,
                -- Correcciones automáticas
                COALESCE((
                    SELECT count(*) 
                    FROM triage_audit_log al 
                    WHERE al.triage_case_id = tc.id AND al.action = 'AUTO_CORRECTION'
                ), 0) AS correcciones_auto,
                -- Detalle de correcciones automáticas
                (
                    SELECT jsonb_agg(jsonb_build_object(
                        'type', al.details->>'correction_type',
                        'fields', al.details->>'fields_changed',
                        'trigger', al.details->>'trigger',
                        'timestamp', al.created_at
                    )) 
                    FROM triage_audit_log al 
                    WHERE al.triage_case_id = tc.id AND al.action = 'AUTO_CORRECTION'
                ) AS auto_corrections_detail,
                -- Detalle de correcciones manuales
                (
                    SELECT jsonb_agg(jsonb_build_object(
                        'fields', al.details->>'corrected_fields',
                        'timestamp', al.created_at,
                        'user', al.performed_by
                    )) 
                    FROM triage_audit_log al 
                    WHERE al.triage_case_id = tc.id AND al.action = 'CORRECTED'
                ) AS manual_corrections_detail
            FROM triage_cases tc
            {where_clause}
            ORDER BY tc.created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = await session.execute(
            query, 
            {"limit": limit or 10000, "offset": offset}
        )
        
        rows = []
        for row in result:
            # Calcular diff de campos corregidos (original vs final)
            orig = row.original_dossier_data or {}
            final = row.dossier_data or {}
            
            # Comparar campos clave
            fields_changed = []
            for section in ['beneficiary', 'related_adults', 'education', 'medical', 'permissions', 'religion']:
                orig_section = orig.get(section, {})
                final_section = final.get(section, {})
                if isinstance(orig_section, dict) and isinstance(final_section, dict):
                    for key in set(list(orig_section.keys()) + list(final_section.keys())):
                        ov = orig_section.get(key)
                        fv = final_section.get(key)
                        if ov != fv:
                            fields_changed.append({
                                "section": section,
                                "field": key,
                                "original": ov,
                                "final": fv
                            })
            
            rows.append({
                "id": str(row.id),
                "batch_id": str(row.batch_id),
                "dni_reference": row.dni_reference,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
                "resolved_by": str(row.resolved_by) if row.resolved_by else None,
                "status": row.status,
                "verdict": row.verdict,
                "errores_iniciales": row.errores_iniciales,
                "errores_finales": row.errores_finales,
                "warnings_finales": row.warnings_finales,
                "ai_insights_finales": row.ai_insights_finales,
                "correcciones_usuario": row.correcciones_usuario,
                "correcciones_auto": row.correcciones_auto,
                "campos_cambiados": fields_changed,
                "auto_corrections_detail": row.auto_corrections_detail,
                "manual_corrections_detail": row.manual_corrections_detail,
                "dossier_data": row.dossier_data,
                "original_dossier_data": row.original_dossier_data,
            })
        
        return rows


def write_json(data: list[dict], filepath: Path):
    """Escribe JSON con formato legible."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"OK JSON guardado en: {filepath} ({len(data)} expedientes)")


def write_excel(data: list[dict], filepath: Path):
    """Escribe Excel con múltiples hojas."""
    wb = openpyxl.Workbook()
    
    # Hoja 1: Resumen por expediente
    ws1 = wb.active
    ws1.title = "Resumen Expedientes"
    
    headers = [
        "ID Expediente", "Batch ID", "DNI Referencia",
        "Creado en", "Terminado en", "Resuelto en", "Resuelto por",
        "Estado", "Veredicto",
        "Errores Iniciales", "Errores Finales", "Warnings Finales", "AI Insights Finales",
        "Correcciones Usuario", "Correcciones Auto",
        "Duración (minutos)"
    ]
    
    # Estilo header
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
    
    for row_idx, item in enumerate(data, 2):
        # Calcular duración en minutos
        duracion = None
        if item["created_at"] and item["completed_at"]:
            try:
                ini = datetime.fromisoformat(item["created_at"].replace('Z', '+00:00'))
                fin = datetime.fromisoformat(item["completed_at"].replace('Z', '+00:00'))
                duracion = round((fin - ini).total_seconds() / 60, 1)
            except:
                pass
        
        values = [
            item["id"],
            item["batch_id"],
            item["dni_reference"],
            item["created_at"],
            item["completed_at"],
            item["resolved_at"],
            item["resolved_by"],
            item["status"],
            item["verdict"],
            item["errores_iniciales"],
            item["errores_finales"],
            item["warnings_finales"],
            item["ai_insights_finales"],
            item["correcciones_usuario"],
            item["correcciones_auto"],
            duracion,
        ]
        
        for col, val in enumerate(values, 1):
            ws1.cell(row=row_idx, column=col, value=val)
    
    # Ajustar ancho columnas
    for col in ws1.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        ws1.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
    
    # Hoja 2: Detalle de correcciones automáticas
    ws2 = wb.create_sheet("Correcciones Auto")
    headers2 = ["Expediente ID", "DNI Ref", "Timestamp", "Tipo", "Campos", "Trigger", "Detalle Maestro"]
    for col, h in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    
    row_idx = 2
    for item in data:
        if item["auto_corrections_detail"]:
            for corr in item["auto_corrections_detail"]:
                ws2.cell(row=row_idx, column=1, value=item["id"])
                ws2.cell(row=row_idx, column=2, value=item["dni_reference"])
                ws2.cell(row=row_idx, column=3, value=corr.get("timestamp"))
                ws2.cell(row=row_idx, column=4, value=corr.get("type"))
                ws2.cell(row=row_idx, column=5, value=corr.get("fields"))
                ws2.cell(row=row_idx, column=6, value=corr.get("trigger"))
                ws2.cell(row=row_idx, column=7, value=str(corr.get("master_match") or ""))
                row_idx += 1
    
    # Hoja 3: Detalle de correcciones manuales
    ws3 = wb.create_sheet("Correcciones Usuario")
    headers3 = ["Expediente ID", "DNI Ref", "Timestamp", "Usuario", "Campos Corregidos"]
    for col, h in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    
    row_idx = 2
    for item in data:
        if item["manual_corrections_detail"]:
            for corr in item["manual_corrections_detail"]:
                ws3.cell(row=row_idx, column=1, value=item["id"])
                ws3.cell(row=row_idx, column=2, value=item["dni_reference"])
                ws3.cell(row=row_idx, column=3, value=corr.get("timestamp"))
                ws3.cell(row=row_idx, column=4, value=corr.get("user"))
                ws3.cell(row=row_idx, column=4, value=str(corr.get("fields") or ""))
                row_idx += 1
    
    # Hoja 4: Campos cambiados (diff original vs final)
    ws4 = wb.create_sheet("Campos Cambiados")
    headers4 = ["Expediente ID", "DNI Ref", "Sección", "Campo", "Original", "Final"]
    for col, h in enumerate(headers4, 1):
        cell = ws4.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    
    row_idx = 2
    for item in data:
        for change in item["campos_cambiados"]:
            ws4.cell(row=row_idx, column=1, value=item["id"])
            ws4.cell(row=row_idx, column=2, value=item["dni_reference"])
            ws4.cell(row=row_idx, column=3, value=change["section"])
            ws4.cell(row=row_idx, column=4, value=change["field"])
            ws4.cell(row=row_idx, column=5, value=str(change["original"]))
            ws4.cell(row=row_idx, column=6, value=str(change["final"]))
            row_idx += 1
    
    wb.save(filepath)
    print(f"OK Excel guardado en: {filepath} ({len(data)} expedientes, 4 hojas)")


async def main():
    parser = argparse.ArgumentParser(description="Exportar datos de auditoría para tesis")
    parser.add_argument("--batch-id", type=str, help="UUID del lote (opcional)")
    parser.add_argument("--all", action="store_true", help="Exportar todos los lotes")
    parser.add_argument("--output", choices=["json", "excel", "both"], default="both", help="Formato de salida")
    parser.add_argument("--file", type=str, required=True, help="Archivo de salida (sin extensión)")
    parser.add_argument("--limit", type=int, help="Límite de expedientes")
    parser.add_argument("--offset", type=int, default=0, help="Offset para paginación")
    
    args = parser.parse_args()
    
    if not args.batch_id and not args.all:
        parser.error("Debe especificar --batch-id o --all")
    
    batch_id = UUID(args.batch_id) if args.batch_id else None
    
    print(f"Exportando datos... (batch_id={batch_id or 'TODOS'}, limit={args.limit or 'sin límite'})")
    
    data = await export_thesis_data(batch_id=batch_id, limit=args.limit, offset=args.offset)
    
    if not data:
        print("No se encontraron expedientes")
        return
    
    base_path = Path(args.file)
    
    if args.output in ("json", "both"):
        write_json(data, base_path.with_suffix(".json"))
    
    if args.output in ("excel", "both"):
        write_excel(data, base_path.with_suffix(".xlsx"))
    
    # Stats resumen
    total = len(data)
    con_errores_iniciales = sum(1 for d in data if d["errores_iniciales"] > 0)
    con_correcciones_usuario = sum(1 for d in data if d["correcciones_usuario"] > 0)
    con_correcciones_auto = sum(1 for d in data if d["correcciones_auto"] > 0)
    auto_aprobados = sum(1 for d in data if d["verdict"] == "AUTO_APPROVED")
    manual_aprobados = sum(1 for d in data if d["verdict"] == "MANUALLY_APPROVED")
    
    print(f"\n=== RESUMEN ===")
    print(f"Total expedientes: {total}")
    print(f"Con errores iniciales: {con_errores_iniciales}")
    print(f"Corregidos por usuario: {con_correcciones_usuario}")
    print(f"Con correcciones automáticas: {con_correcciones_auto}")
    print(f"AUTO_APPROVED: {auto_aprobados}")
    print(f"MANUALLY_APPROVED: {manual_aprobados}")


if __name__ == "__main__":
    asyncio.run(main())