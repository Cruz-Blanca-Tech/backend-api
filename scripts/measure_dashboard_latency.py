"""RNF-02: mide el tiempo de respuesta de los endpoints del dashboard.

Uso (desde backend-api, con el backend corriendo):
    python scripts/measure_dashboard_latency.py --base-url https://<backend> --token <JWT> --runs 20

El JWT es el `access_token` de una sesión iniciada (cookie `access_token` en el
navegador). El script hace `--runs` peticiones a cada endpoint, informa la mediana,
el percentil 95 y el máximo, y lo compara con el umbral de la ERS (5 s). Guarda el
detalle en `rnf02_latencia_dashboards.csv` para anexarlo como evidencia.
"""
import argparse
import csv
import statistics
import sys
import time

import httpx

ENDPOINTS = [
    "/api/v1/reporting/operations/daily-volume",
    "/api/v1/reporting/operations/success-rate",
    "/api/v1/reporting/operations/automation-level",
    "/api/v1/reporting/demographics/registration-growth",
    "/api/v1/reporting/demographics/population-pyramid",
]
UMBRAL_S = 5.0


def p95(values):
    ordered = sorted(values)
    return ordered[max(0, int(round(0.95 * len(ordered))) - 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--out", default="rnf02_latencia_dashboards.csv")
    args = parser.parse_args()

    headers = {"Authorization": f"Bearer {args.token}"}
    rows, cumple = [], True
    with httpx.Client(base_url=args.base_url.rstrip("/"), headers=headers, timeout=30) as client:
        for path in ENDPOINTS:
            client.get(path)  # calentamiento (no se mide)
            tiempos = []
            for _ in range(args.runs):
                t0 = time.perf_counter()
                res = client.get(path)
                tiempos.append(time.perf_counter() - t0)
                if res.status_code != 200:
                    print(f"ERROR {res.status_code} en {path}: {res.text[:200]}")
                    return 2
            med, q95, mx = statistics.median(tiempos), p95(tiempos), max(tiempos)
            ok = q95 < UMBRAL_S
            cumple &= ok
            rows.append([path, args.runs, f"{med:.3f}", f"{q95:.3f}", f"{mx:.3f}", "CUMPLE" if ok else "NO CUMPLE"])
            print(f"{path:55s} mediana={med:.3f}s p95={q95:.3f}s max={mx:.3f}s {'OK' if ok else 'SUPERA 5 s'}")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["endpoint", "ejecuciones", "mediana_s", "p95_s", "max_s", "resultado_rnf02"])
        w.writerows(rows)
    print(f"\nRNF-02 (p95 < {UMBRAL_S} s): {'CUMPLE' if cumple else 'NO CUMPLE'}. Detalle en {args.out}")
    return 0 if cumple else 1


if __name__ == "__main__":
    sys.exit(main())
