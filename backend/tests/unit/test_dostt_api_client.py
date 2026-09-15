import httpx
import pytest

from app.integrations import dostt_api_client
from app.integrations.dostt_api_client import DosttApiError, create_ticket


def _transport(handler):
    return httpx.MockTransport(handler)


def test_create_ticket_sends_confirmed_request_shape(tmp_path):
    image = tmp_path / "shot.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10)

    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(201, json={"message": "Ticket submitted successfully", "ticket_id": 2119})

    ticket_id = create_ticket(
        auth_token="tok123",
        description="Coins deducted but no call happened",
        language_id=1,
        is_call_opted_in=True,
        user_type=0,
        issue_id=37,
        country_code="IN",
        image_path=str(image),
        transport=_transport(handler),
    )

    assert ticket_id == 2119
    req = captured["request"]
    assert req.method == "POST"
    assert str(req.url) == "https://testdostt.getlokalapp.com/help-and-support/tickets/"
    assert req.headers["JWT-AUTHORIZATION"] == "Bearer tok123"
    assert req.headers["X-Country-Code"] == "IN"
    assert req.headers["Content-Type"].startswith("multipart/form-data")

    body = req.content.decode("utf-8", errors="replace")
    assert 'name="description"' in body
    assert "Coins deducted but no call happened" in body
    assert 'name="languages"' in body and "\r\n\r\n1\r\n" in body
    assert 'name="is_call_opted_in"' in body and "true" in body
    assert 'name="type"' in body
    assert 'name="issues"' in body and "37" in body
    assert 'name="files"' in body
    assert "shot.png" in body


def test_create_ticket_without_image_omits_files_part():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"message": "ok", "ticket_id": 42})

    ticket_id = create_ticket(
        auth_token="tok123",
        description="test",
        language_id=1,
        is_call_opted_in=False,
        user_type=0,
        issue_id=37,
        transport=_transport(handler),
    )
    assert ticket_id == 42


def test_create_ticket_raises_on_non_201():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": {"issues": ["Invalid pk \"361\" - object does not exist."]}})

    with pytest.raises(DosttApiError) as exc_info:
        create_ticket(
            auth_token="tok123",
            description="test",
            language_id=1,
            is_call_opted_in=False,
            user_type=0,
            issue_id=361,
            transport=_transport(handler),
        )
    assert exc_info.value.status_code == 400
    assert "361" in exc_info.value.body


def test_headers_include_app_version_and_platform():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["app-version"] == dostt_api_client.settings.DOSTT_APP_VERSION
        assert request.headers["X-Platform-Type"] == "Android"
        assert request.headers["Service-Type"] == "1"
        return httpx.Response(201, json={"message": "ok", "ticket_id": 1})

    create_ticket(
        auth_token="tok",
        description="test",
        language_id=1,
        is_call_opted_in=False,
        user_type=0,
        issue_id=1,
        transport=_transport(handler),
    )


def test_app_version_override_is_sent_when_given():
    # Confirmed 2026-09-11: the real webview hand-off includes ?version=,
    # the real app version — more accurate than the hardcoded setting.
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["app-version"] == "1.1.38"
        assert request.headers["app-version-code"] == dostt_api_client.settings.DOSTT_APP_VERSION_CODE
        return httpx.Response(201, json={"message": "ok", "ticket_id": 1})

    create_ticket(
        auth_token="tok", description="test", language_id=1, is_call_opted_in=False,
        user_type=0, issue_id=1, app_version="1.1.38", transport=_transport(handler),
    )
