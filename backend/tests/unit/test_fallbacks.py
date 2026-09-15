"""Proves the 2026-09-10 fix: check_fallbacks() now actually uses
GIBBERISH_RESPONSE (previously dead code, despite existing), without
regressing the existing sensitive-pattern list or misfiring on legitimate
messages. See the module docstring for why OFFTOPIC_RESPONSE deliberately
stays unwired here (a first attempt wrongly flagged normal on-topic
messages) — that fix is a system-prompt instruction instead (agent/prompt.py),
which can only be meaningfully verified against a real Gemini call, not a
fake-client unit test, so it's confirmed via live testing rather than here.
"""

from app.data.fallbacks import check_fallbacks


def test_existing_sensitive_pattern_still_works():
    fb = check_fallbacks("I'm 15 years old")
    assert fb is not None
    assert fb.id == "underage"
    assert fb.ends_session is True


def test_app_related_question_is_not_flagged():
    assert check_fallbacks("Why was I charged for a call I didn't make?") is None


def test_short_conversational_replies_are_not_flagged():
    for reply in ("yes", "no", "ok", "sure", "thanks"):
        assert check_fallbacks(reply) is None, f"{reply!r} was wrongly flagged"


def test_long_gibberish_is_flagged():
    fb = check_fallbacks("xkcd zzzbrqt qwrtplk")
    assert fb is not None
    assert fb.id == "gibberish"


def test_normal_greeting_is_not_flagged():
    assert check_fallbacks("Hi, I need some help please") is None


def test_offtopic_question_is_not_code_level_flagged():
    # Confirms the deliberate design choice: this is NOT caught here (it's a
    # system-prompt instruction instead) — see agent/prompt.py.
    assert check_fallbacks("What is the capital of France?") is None
