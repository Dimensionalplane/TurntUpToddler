import pytest
from fastapi.testclient import TestClient
from hymn_remaker.api import app

client = TestClient(app)

def test_system_status():
    response = client.get("/api/v1/system")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "success"

def test_radio_status():
    response = client.get("/api/v1/radio/status")
    assert response.status_code == 200
    assert "status" in response.json()
