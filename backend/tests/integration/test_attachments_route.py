import io

from app.services import chat_session_service


def _session_id(db, account):
    return chat_session_service.start_session(db, account.id, "en").id


def test_upload_attachment_succeeds(client, db, account):
    session_id = _session_id(db, account)
    resp = client.post(
        f"/api/session/{session_id}/attachment",
        files={"file": ("shot.png", io.BytesIO(b"fake-png-bytes"), "image/png")},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "attached"


def test_upload_attachment_unknown_session_is_404(client):
    resp = client.post(
        "/api/session/does-not-exist/attachment",
        files={"file": ("shot.png", io.BytesIO(b"data"), "image/png")},
    )
    assert resp.status_code == 404


def test_upload_attachment_rejects_bad_content_type(client, db, account):
    session_id = _session_id(db, account)
    resp = client.post(
        f"/api/session/{session_id}/attachment",
        files={"file": ("doc.pdf", io.BytesIO(b"data"), "application/pdf")},
    )
    assert resp.status_code == 400


def test_remove_attachment(client, db, account):
    session_id = _session_id(db, account)
    client.post(
        f"/api/session/{session_id}/attachment",
        files={"file": ("shot.png", io.BytesIO(b"data"), "image/png")},
    )
    resp = client.delete(f"/api/session/{session_id}/attachment")
    assert resp.status_code == 200
    assert resp.json()["status"] == "removed"

    resp2 = client.delete(f"/api/session/{session_id}/attachment")
    assert resp2.json()["status"] == "nothing_pending"
