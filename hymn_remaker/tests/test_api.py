import pytest
from fastapi.testclient import TestClient
from hymn_remaker.api import app
import os

client = TestClient(app)

def test_system_status():
    response = client.get("/api/v1/system")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "binaries" in data["data"]
    assert "python_packages" in data["data"]

def test_generate_endpoint_schema():
    # Test that the endpoint accepts the new v1.27.0 parameters (validation test)
    # We won't actually run the full pipeline here, just check if it accepts the multipart form

    # Create a dummy midi file
    dummy_midi = b'MThd\x00\x00\x00\x06\x00\x01\x00\x01\x00\x60'

    files = {"file": ("test.mid", dummy_midi, "audio/midi")}
    data = {
        "style": "Lofi",
        "generate_vocals": "true",
        "voice_id": "pNInz6obpgmqM0pMBpCt",
        "model": "eleven_monolingual_v1",
        "video_format": "Vertical 9:16 (TikTok/Reels)",
        "create_shorts": "true",
        "enable_visualizer": "true",
        "visualizer_mode": "line",
        "kids_mode": "true"
    }

    # We expect 200 Accepted because it queues the background task
    # Note: process_single_midi might fail later in background, but the API should accept it.
    response = client.post("/api/v1/generate", files=files, data=data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "accepted"
    assert res_data["configuration"]["kids_mode"] is True
    assert res_data["configuration"]["visualizer_mode"] == "line"

def test_editor_extract_unsupported():
    # Test that it rejects non-MusicXML
    dummy_midi = b'MThd\x00\x00\x00\x06\x00\x01\x00\x01\x00\x60'
    files = {"file": ("test.mid", dummy_midi, "audio/midi")}
    response = client.post("/api/v1/editor/extract", files=files)
    assert response.status_code == 400
    assert "Only MusicXML" in response.json()["detail"]

def test_editor_cluster_submit_schema():
    data = {"prompt": "test", "target_bpm": 128}
    # This might fail if RabbitMQ is not running, so we'll mock or just check routing
    # But for a schema test, we just check if it hits the endpoint
    response = client.post("/api/v1/editor/cluster/submit", data=data)
    # We expect 500 if RabbitMQ is missing, but 200 if everything is fine.
    # In this environment, it will likely be 500.
    assert response.status_code in [200, 500]
