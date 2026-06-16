# start.ps1 - Levanta el backend-api de Cruz Blanca
# Uso:  .\start.ps1
$ErrorActionPreference = "Stop"
$proj = $PSScriptRoot

Write-Host "==> 1/3 Levantando base de datos PostgreSQL (Docker)..." -ForegroundColor Cyan
docker compose -f "$proj\docker-compose.yml" up -d

Write-Host "==> 2/3 Aplicando migraciones (Alembic)..." -ForegroundColor Cyan
& "$proj\.venv\Scripts\python.exe" -m alembic upgrade head

Write-Host "==> 3/3 Iniciando API (FastAPI/uvicorn) en http://localhost:8000 ..." -ForegroundColor Cyan
Write-Host "    Docs interactivas: http://localhost:8000/docs" -ForegroundColor Green
& "$proj\.venv\Scripts\python.exe" -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
