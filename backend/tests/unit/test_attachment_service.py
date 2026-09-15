import os
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import attachment_service


def _fake_upload(content_type="image/png", filename="shot.png"):
    return SimpleNamespace(content_type=content_type, filename=filename)


def _session(db, account):
    from app.services import chat_session_service
    return chat_session_service.start_session(db, account.id, "en")


def test_save_and_get_pending_attachment(db, account):
    session = _session(db, account)
    saved = attachment_service.save_pending_attachment(db, session.id, _fake_upload(), b"fake-image-bytes")

    assert os.path.exists(saved.file_path)
    fetched = attachment_service.get_pending_attachment(db, session.id)
    assert fetched.id == saved.id


def test_rejects_unsupported_content_type(db, account):
    session = _session(db, account)
    with pytest.raises(attachment_service.AttachmentError):
        attachment_service.save_pending_attachment(db, session.id, _fake_upload(content_type="application/pdf"), b"x")


def test_rejects_oversized_file(db, account, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_MAX_BYTES", 10)
    session = _session(db, account)
    with pytest.raises(attachment_service.AttachmentError):
        attachment_service.save_pending_attachment(db, session.id, _fake_upload(), b"x" * 100)


def test_uploading_again_replaces_previous_pending_one(db, account):
    session = _session(db, account)
    first = attachment_service.save_pending_attachment(db, session.id, _fake_upload(), b"first")
    first_path = first.file_path

    second = attachment_service.save_pending_attachment(db, session.id, _fake_upload(), b"second")

    assert not os.path.exists(first_path)  # old file cleaned up
    assert attachment_service.get_pending_attachment(db, session.id).id == second.id


def test_consume_deletes_row_but_leaves_file_on_disk(db, account):
    session = _session(db, account)
    saved = attachment_service.save_pending_attachment(db, session.id, _fake_upload(), b"data")

    consumed = attachment_service.consume_pending_attachment(db, session.id)

    assert consumed.file_path == saved.file_path
    assert os.path.exists(consumed.file_path)
    assert attachment_service.get_pending_attachment(db, session.id) is None


def test_consume_with_nothing_pending_returns_none(db, account):
    session = _session(db, account)
    assert attachment_service.consume_pending_attachment(db, session.id) is None


def test_clear_deletes_row_and_file(db, account):
    session = _session(db, account)
    saved = attachment_service.save_pending_attachment(db, session.id, _fake_upload(), b"data")

    removed = attachment_service.clear_pending_attachment(db, session.id)

    assert removed is True
    assert not os.path.exists(saved.file_path)
    assert attachment_service.get_pending_attachment(db, session.id) is None


def test_clear_with_nothing_pending_returns_false(db, account):
    session = _session(db, account)
    assert attachment_service.clear_pending_attachment(db, session.id) is False
