import openpyxl

import os
GT_PATH = r"C:\Users\enzot\Documents\code\CruzBlanca\Ground truth\Excel\ground truth.xlsx"
wb = openpyxl.load_workbook(GT_PATH, data_only=True)
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
