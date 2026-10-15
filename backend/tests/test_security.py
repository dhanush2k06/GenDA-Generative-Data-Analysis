"""
Security test suite:
- Rejection of unauthenticated requests
- Rejection of foreign origins
- Loopback health check
- Session isolation and clearing
"""

from fastapi.testclient import TestClient
from genda.api.app import app
from genda.api.security import get_active_token, set_active_token
from tests.fixtures.synthetic_data import SYNTHETIC_CSV_BYTES

client = TestClient(app, base_url="http://127.0.0.1:8000")


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["loopback_only"] is True


def test_auth_rejection():
    # Attempting to upload without token
    res = client.post(
        "/api/session/upload",
        files={"file": ("test.csv", SYNTHETIC_CSV_BYTES, "text/csv")},
    )
    assert res.status_code == 401


def test_foreign_origin_rejected():
    token = get_active_token()
    res = client.post(
        "/api/session/upload",
        headers={"X-GenDA-Token": token, "Origin": "http://evil-attacker.com"},
        files={"file": ("test.csv", SYNTHETIC_CSV_BYTES, "text/csv")},
    )
    assert res.status_code == 403


def test_session_lifecycle_and_clear():
    token = get_active_token()
    headers = {"X-GenDA-Token": token}

    # 1. Upload CSV
    res = client.post(
        "/api/session/upload",
        headers=headers,
        files={"file": ("synthetic.csv", SYNTHETIC_CSV_BYTES, "text/csv")},
    )
    assert res.status_code == 200
    preview = res.json()
    session_id = preview["session_id"]
    assert preview["row_count"] == 5

    # 2. Profile
    res_prof = client.post(f"/api/session/{session_id}/profile", headers=headers)
    assert res_prof.status_code == 200
    assert res_prof.json()["row_count"] == 5

    # 3. Analyze
    req_body = {
        "operation": "numeric_summary",
        "column": "amount",
    }
    res_an = client.post(f"/api/session/{session_id}/analyze", headers=headers, json=req_body)
    assert res_an.status_code == 200
    assert res_an.json()["validation_status"] == "passed"

    # 4. Clear Session
    res_del = client.delete(f"/api/session/{session_id}", headers=headers)
    assert res_del.status_code == 200

    # 5. Verify it's gone
    res_gone = client.get(f"/api/session/{session_id}", headers=headers)
    assert res_gone.status_code == 404
