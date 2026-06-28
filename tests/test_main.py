import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Bienvenido" in response.json()["message"]
    assert response.json()["status"] == "active"

def test_security_health():
    response = client.get("/auth/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "context": "Security & Access"}

def test_intake_health():
    response = client.get("/api/v1/intake/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "context": "Document Intake & OCR"}

def test_triage_health():
    response = client.get("/api/v1/triage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "context": "Data Quality & Triage"}

def test_reporting_health():
    response = client.get("/api/v1/reporting/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "context": "Reporting & Analytics"}
