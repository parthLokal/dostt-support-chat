"""Best-effort, UNVERIFIED read of the real Dostt access token's own
payload claims (user_type, country — see the real token structure captured
2026-09-08: {"user_id":..., "user_payload":{"user_type":0,"country":"IN",
"onboarded_language_id":1,...}, "iss":"getlokalapp.com"}).

Deliberately does not verify the signature — that would need Dostt's own
signing secret/public key, which is an engineering-team dependency this
project has been told to defer. This extends the exact same trust level
already given to `user_id` in the webview URL (also unverified, also just
base64-decoded — see api/routes/session.py's _decode_banner_user_id): both
assume the token/id arrived from the real app's own legitimate webview
hand-off, not from an untrusted caller. The actual security boundary for
anything that matters (creating a real ticket) is Dostt's own backend,
which DOES verify the signature and will reject a forged/expired token —
see dostt_api_client.py.

Used only as a fallback source for fields the host app would otherwise have
to pass as separate URL params (user_type_code, country_code) — see
ticket_service._mirror_to_real_api. Never used to override an explicitly
supplied value, and never trusted for anything security-sensitive on our
own side.
"""

import base64
import json


def decode_unverified_claims(token: str | None) -> dict | None:
    if not token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload_b64 = parts[1]
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def user_type_from_token(token: str | None) -> int | None:
    claims = decode_unverified_claims(token)
    if claims is None:
        return None
    value = claims.get("user_payload", {}).get("user_type")
    return value if isinstance(value, int) else None


def country_from_token(token: str | None) -> str | None:
    claims = decode_unverified_claims(token)
    if claims is None:
        return None
    value = claims.get("user_payload", {}).get("country")
    return value if isinstance(value, str) and value else None
