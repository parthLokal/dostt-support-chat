from app.models.account import Account
from app.models.call import Call
from app.models.enums import AccountRole
from app.services import refund_service


def _account(**overrides) -> Account:
    defaults = dict(
        user_id="u1", name="Test", role=AccountRole.USER,
        ltv_value_inr=2500, tickets_raised=10, refunded_tickets=8,
        ltv_coins=5000, refund_coins_lifetime=500,
    )
    defaults.update(overrides)
    return Account(**defaults)


def _call(**overrides) -> Call:
    defaults = dict(call_type="audio", duration_sec=30, coins_debited=20, counterpart_name="X")
    defaults.update(overrides)
    return Call(**defaults)


def test_non_refund_driven_tag_is_never_eligible():
    decision = refund_service.decide(_account(), _call(), "some_other_issue")
    assert not decision.eligible


def test_zero_coins_debited_is_never_eligible_regardless_of_segment():
    """Confirmed against real production data (2026-09-08 audit): calls under
    ~10s of talktime carry coins_debited=0 — nothing was actually charged, so
    there's nothing to refund, no matter how high the LTV segment or how
    genuine the account's history is."""
    account = _account(ltv_value_inr=19754.2, tickets_raised=32, refunded_tickets=16)  # very_high, 50% ratio
    call = _call(call_type="audio", duration_sec=5, coins_debited=0)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert not decision.eligible
    assert decision.rule_label == "No charge on this call"


def test_zero_coins_debited_blocks_cannot_hear_too():
    account = _account(ltv_coins=10000, refund_coins_lifetime=165)  # refund_ltv_ratio well under 20%
    call = _call(call_type="audio", duration_sec=2, coins_debited=0)
    decision = refund_service.decide(account, call, "cannot_hear")
    assert not decision.eligible


def test_very_high_ltv_full_refund_when_within_window():
    account = _account(ltv_value_inr=21500)
    call = _call(call_type="audio", duration_sec=200, coins_debited=130)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert decision.eligible
    assert decision.refund_coins == 130
    assert "Very High" in decision.rule_label


def test_very_high_ltv_not_eligible_outside_coin_cap():
    account = _account(ltv_value_inr=21500)
    call = _call(call_type="audio", duration_sec=100, coins_debited=200)  # >= 150 coins
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert not decision.eligible


def test_duration_at_or_above_50s_is_never_eligible_below_very_high():
    account = _account(ltv_value_inr=8681, tickets_raised=10, refunded_tickets=9)
    call = _call(duration_sec=50)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert not decision.eligible
    assert "Duration" in decision.rule_label


def test_high_ltv_first_time_user_skips_history_check():
    account = _account(ltv_value_inr=8681, tickets_raised=0, refunded_tickets=0)
    call = _call(call_type="video", duration_sec=10, coins_debited=60)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert decision.eligible
    assert decision.refund_coins == 60  # video 1-min charge
    assert "first-time" in decision.rule_label


def test_high_ltv_genuine_history_over_70_percent_eligible():
    account = _account(ltv_value_inr=8681, tickets_raised=10, refunded_tickets=9)  # 90%
    call = _call(call_type="audio", duration_sec=45, coins_debited=20)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert decision.eligible
    assert decision.refund_coins == 10  # audio 1-min charge


def test_high_ltv_abuse_pattern_below_70_percent_blocked():
    """The PRD's core promise: block repeat abusers even though they've raised
    plenty of tickets — this is the exact scenario the v1.1 rule exists for."""
    account = _account(ltv_value_inr=8000, tickets_raised=46, refunded_tickets=30)  # ~65%
    call = _call(duration_sec=18)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert not decision.eligible
    assert "below 70%" in decision.rule_label


def test_mid_ltv_genuine_history_under_spend_cap_eligible():
    account = _account(ltv_value_inr=2400, tickets_raised=13, refunded_tickets=11, ltv_coins=7830, refund_coins_lifetime=900)
    call = _call(call_type="video", duration_sec=45, coins_debited=60)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert decision.eligible


def test_mid_ltv_spend_cap_exceeded_blocks_even_with_genuine_history():
    account = _account(ltv_value_inr=2400, tickets_raised=13, refunded_tickets=11, ltv_coins=1000, refund_coins_lifetime=300)  # 30% > 20% cap
    call = _call(duration_sec=30)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert not decision.eligible
    assert "spend cap" in decision.rule_label


def test_low_ltv_first_time_still_checks_spend_cap():
    account = _account(ltv_value_inr=500, tickets_raised=0, refunded_tickets=0, ltv_coins=450, refund_coins_lifetime=200)  # ~44% > 20%
    call = _call(duration_sec=30)
    decision = refund_service.decide(account, call, "charged_incorrectly")
    assert not decision.eligible


def test_cannot_hear_eligible_under_20_percent_refund_ltv_ratio():
    account = _account(ltv_coins=5000, refund_coins_lifetime=500)  # 10%
    call = _call(call_type="video", duration_sec=200, coins_debited=140)
    decision = refund_service.decide(account, call, "cannot_hear")
    assert decision.eligible
    assert decision.refund_coins == 60


def test_not_showing_face_blocked_over_20_percent_refund_ltv_ratio():
    account = _account(ltv_coins=1000, refund_coins_lifetime=300)  # 30%
    call = _call(duration_sec=200)
    decision = refund_service.decide(account, call, "not_showing_face")
    assert not decision.eligible


def test_ltv_segment_boundaries():
    assert refund_service.ltv_segment(15001) == "very_high"
    assert refund_service.ltv_segment(15000) == "high"
    assert refund_service.ltv_segment(5000) == "high"
    assert refund_service.ltv_segment(4999) == "mid"
    assert refund_service.ltv_segment(1000) == "mid"
    assert refund_service.ltv_segment(999) == "low"
