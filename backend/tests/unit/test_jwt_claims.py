"""Proves the 2026-09-11 fix: deriving user_type/country/language from the
real Dostt access token's own (unverified) claims, instead of requiring the
host app to pass them as separate URL params — see app/core/jwt_claims.py's
own docstring for why signature verification is deliberately skipped.
"""

import base64
import json

from app.core.jwt_claims import country_from_token, decode_unverified_claims, user_type_from_token


def _fake_token(payload: dict) -> str:
    def b64(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'HS256'})}.{b64(payload)}.fake-signature"


_REAL_SHAPED_PAYLOAD = {
    "token_type": "access",
    "user_id": 12345,
    "user_payload": {"user_type": 1, "country": "IN", "onboarded_language_id": 3},
    "iss": "getlokalapp.com",
}


def test_decodes_a_well_formed_token():
    token = _fake_token(_REAL_SHAPED_PAYLOAD)
    claims = decode_unverified_claims(token)
    assert claims["user_id"] == 12345
    assert claims["user_payload"]["country"] == "IN"


def test_user_type_and_country_extracted_correctly():
    token = _fake_token(_REAL_SHAPED_PAYLOAD)
    assert user_type_from_token(token) == 1
    assert country_from_token(token) == "IN"


def test_none_token_returns_none_everywhere():
    assert decode_unverified_claims(None) is None
    assert user_type_from_token(None) is None
    assert country_from_token(None) is None


def test_malformed_token_degrades_to_none_not_an_exception():
    assert decode_unverified_claims("not-a-jwt") is None
    assert decode_unverified_claims("only.two-parts") is None
    assert decode_unverified_claims("a.b.c") is None  # 3 parts but not valid base64/JSON
    assert user_type_from_token("garbage") is None
    assert country_from_token("garbage") is None


def test_missing_claim_returns_none_not_a_crash():
    token = _fake_token({"user_id": 1, "user_payload": {}})
    assert user_type_from_token(token) is None
    assert country_from_token(token) is None
