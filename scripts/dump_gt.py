import os
import sys
import openpyxl

gt_path = sys.argv[1] if len(sys.argv) > 1 else os.getenv("GT_PATH", r"Ground truth/Excel/ground truth.xlsx")
if not os.path.exists(gt_path):
    print(f"Archivo no encontrado: {gt_path}. Uso: python dump_gt.py <ruta_al_excel>")
    sys.exit(1)

wb = openpyxl.load_workbook(gt_path, data_only=True)
s = wb.active
headers = [c.value for c in s[4]]

for r_idx in range(6, 12):
    row_vals = [s.cell(row=r_idx, column=c).value for c in range(1, len(headers) + 1)]
    exp = row_vals[0]
    dni = row_vals[1]
    print(f"=== {exp} (DNI {dni}) ===")
    for h, v in zip(headers, row_vals):
        if v is not None:
            print(f"  {h}: {repr(v)}")
