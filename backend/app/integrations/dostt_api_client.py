"""Real ticket-creation API client — POSTs to the actual Dostt backend's own
help-and-support ticket endpoint. Confirmed working end-to-end via a live
curl test on 2026-09-08 (staging, ticket_id=2119).

Wired into ticket_service.py's _mirror_to_real_api. The real webview
hand-off (confirmed 2026-09-11 against an actual captured payload) is
?userId=<plain id>&token=<raw JWT>&version=<app version> — note the URL
param names differ from this module's/ticket_service's own field names
(auth_token, app_version), which is deliberate: the URL contract is the app
engineers' to define, ours is internal.

Field mapping, confirmed empirically against a real decoded access token
(not guessed):
  language_id       -> the account's onboarded_language_id (common_preferredlanguages.id)
  user_type          -> the account's own user_type claim (0 seen for a regular user)
  issue_id           -> a real help_and_support_issue.id — environment-specific (a
                        production id will not exist on staging and vice versa)

Auth is a per-user JWT in a non-standard `JWT-AUTHORIZATION` header — there is
no service/admin credential known to exist yet that can act for an arbitrary
user_id without their own token.
"""

from pathlib import Path

import httpx

from app.core.config import settings

TICKETS_PATH = "/help-and-support/tickets/"


class DosttApiError(RuntimeError):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"Dostt ticket API returned {status_code}: {body}")
        self.status_code = status_code
        self.body = body


def _headers(auth_token: str, country_code: str, app_version: str | None = None) -> dict:
    return {
        "Accept": "application/json, text/plain, */*",
        "JWT-AUTHORIZATION": f"Bearer {auth_token}",
        "Service-Type": "1",
        # Prefers the real user's own app version (from the webview hand-off
        # URL's ?version=, confirmed 2026-09-11) over the hardcoded setting —
        # only falls back to the setting when the host app didn't send one.
        # No equivalent real source for app-version-code exists yet (the
        # hand-off only carries the dotted version string, not a numeric
        # code), so that one still always comes from settings.
        "app-version": app_version or settings.DOSTT_APP_VERSION,
        "app-version-code": settings.DOSTT_APP_VERSION_CODE,
        "X-Country-Code": country_code,
        "X-App-Open-Count": "0",
        "X-Platform-Type": "Android",
    }


def create_ticket(
    *,
    auth_token: str,
    description: str,
    language_id: int,
    is_call_opted_in: bool,
    user_type: int,
    issue_id: int,
    country_code: str = "IN",
    image_path: str | None = None,
    image_content_type: str = "image/jpeg",
    app_version: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> int:
    """Create a real support ticket. Returns the new ticket's id.

    Raises DosttApiError on any non-201 response. `transport` is test-only
    (inject an httpx.MockTransport to avoid a real network call).

    Only the image_path-given path (multipart/form-data) has actually been
    confirmed against the real API (2026-09-08 curl test). Without an image,
    httpx sends application/x-www-form-urlencoded instead — plausible DRF
    accepts that too, but nobody has verified it; don't assume it works
    without testing it for real first.
    """
    data = {
        "description": description,
        "languages": str(language_id),
        "is_call_opted_in": "true" if is_call_opted_in else "false",
        "type": str(user_type),
        "issues": str(issue_id),
    }
    headers = _headers(auth_token, country_code, app_version)
    url = f"{settings.DOSTT_API_BASE_URL}{TICKETS_PATH}"

    with httpx.Client(transport=transport, timeout=30.0) as client:
        if image_path:
            with open(image_path, "rb") as fh:
                files = {"files": (Path(image_path).name, fh, image_content_type)}
                resp = client.post(url, data=data, files=files, headers=headers)
        else:
            resp = client.post(url, data=data, headers=headers)

    if resp.status_code != 201:
        raise DosttApiError(resp.status_code, resp.text)

    return resp.json()["ticket_id"]
