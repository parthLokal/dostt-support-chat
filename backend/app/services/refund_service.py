"""The refund-automation decision engine — "PRD: Dostt | Revised Automated CS
Refund Workflow v1.1". Pure, deterministic business logic: no AI involved, by
design (chatbot PRD: "Gemini only answers through FAQ's" — a refund decision
is never something the model reasons its own way to). As of 2026-09-08 the
model is never told this outcome at all, in either direction — `decide` is
called from app.services.ticket_service.create_ticket_with_automation, which
may resolve a ticket off it, but the chat reply always just says a ticket
was raised for review, regardless of what `decide` returned.

This is the one place these rules are implemented — ticket_service.py and
the tests both call `decide`, never reimplement the thresholds.
"""

from dataclasses import dataclass

from app.models.account import Account
from app.models.call import Call

REFUND_DRIVEN_ISSUE_TAGS = ("charged_incorrectly", "cannot_hear", "not_showing_face")


@dataclass(frozen=True)
class RefundDecision:
    eligible: bool
    rule_label: str
    reason: str
    refund_coins: int = 0


def ltv_segment(ltv_value_inr: float) -> str:
    if ltv_value_inr > 15000:
        return "very_high"
    if ltv_value_inr >= 5000:
        return "high"
    if ltv_value_inr >= 1000:
        return "mid"
    return "low"


# From the "Dostt_Refund SOP" doc's User-Based SLA table (Ultra/High Spend &
# LTE: 0-2 hrs, Mid Tier: 0-4 hrs, Low Spend: 0-6 hrs, New Users: 0-12 hrs) —
# a formal SOP doc distinct from the v1.1 refund-automation PRD above, found
# on a 2026-09-08 sheet audit. Applies to every ticket, not just the three
# refund-driven ones, since the table is framed around account tier, not
# category — see ticket_service.create_ticket, the only place this is used.
def sla_hours_for(account: Account) -> int:
    if account.tickets_raised == 0:
        return 12  # "New" tier, same bypass-the-70%-rule definition used above
    segment = ltv_segment(account.ltv_value_inr)
    if segment in ("very_high", "high"):
        return 2
    if segment == "mid":
        return 4
    return 6  # low


def decide(account: Account, call: Call, issue_tag: str) -> RefundDecision:
    if issue_tag not in REFUND_DRIVEN_ISSUE_TAGS:
        return RefundDecision(
            eligible=False,
            rule_label="Not an automated-refund category",
            reason="This issue type isn't covered by refund automation.",
        )

    # Confirmed against real production data (ticket-level automation dump,
    # 2026-09-08): calls under ~10s worth of talktime carry coins_debited=0 —
    # billing never actually charges for them in the first place, regardless
    # of LTV segment or issue type. "Talktime is Less than 10 seconds" is the
    # real system's own rule_description for this — checked first, before any
    # segment logic, since a fixed per-minute refund on a call that charged
    # nothing would be a nonsensical outcome (and did not match any real
    # eligible=YES row in that data).
    if call.coins_debited <= 0:
        return RefundDecision(
            eligible=False,
            rule_label="No charge on this call",
            reason=(
                f"This call lasted {call.duration_sec}s and no coins were debited for it "
                "(calls under the minimum billing threshold aren't charged at all), so "
                "there's nothing to refund."
            ),
        )

    ratio = account.refunded_tickets / account.tickets_raised if account.tickets_raised > 0 else None
    is_first_time = account.tickets_raised == 0
    refund_ltv_ratio = account.refund_coins_lifetime / account.ltv_coins if account.ltv_coins > 0 else 0.0
    segment = ltv_segment(account.ltv_value_inr)
    per_min_charge = 60 if call.call_type == "video" else 10

    if issue_tag == "charged_incorrectly":
        if segment == "very_high":
            limit_sec = 150 if call.call_type == "video" else 300
            window_label = "2.5 min" if call.call_type == "video" else "5 min"
            if call.duration_sec < limit_sec and call.coins_debited < 150:
                return RefundDecision(
                    eligible=True,
                    refund_coins=call.coins_debited,
                    rule_label="Very High LTV — Full Refund",
                    reason=(
                        f"Call lasted {call.duration_sec}s (under the {window_label} limit) and "
                        f"only {call.coins_debited} coins were consumed (under 150), so this is "
                        "fully refunded automatically."
                    ),
                )
            return RefundDecision(
                eligible=False,
                rule_label="Very High LTV — limits not met",
                reason=(
                    f"This call lasted {call.duration_sec}s and used {call.coins_debited} coins, "
                    "which is outside the automatic full-refund window for Very High LTV users. "
                    "Routed to manual review."
                ),
            )

        if call.duration_sec >= 50:
            return RefundDecision(
                eligible=False,
                rule_label="Duration check failed",
                reason=(
                    f"This call lasted {call.duration_sec}s, which is at or above the "
                    "50-second automatic-refund window, so it needs manual review."
                ),
            )

        if segment == "high":
            if is_first_time:
                return RefundDecision(
                    eligible=True,
                    refund_coins=per_min_charge,
                    rule_label="High LTV — first-time user",
                    reason=(
                        "This is your first-ever ticket, so we skip the ticket-history check. "
                        f"The call lasted {call.duration_sec}s (under 50s), so you get a "
                        "1-minute-charge refund."
                    ),
                )
            if ratio is not None and ratio > 0.7:
                return RefundDecision(
                    eligible=True,
                    refund_coins=per_min_charge,
                    rule_label="High LTV — genuine history",
                    reason=(
                        f"{round(ratio * 100)}% of your past tickets ended in a refund (above "
                        f"the 70% bar), and this call lasted {call.duration_sec}s (under 50s)."
                    ),
                )
            return RefundDecision(
                eligible=False,
                rule_label="High LTV — history below 70%",
                reason=(
                    f"Only {round((ratio or 0) * 100)}% of your past tickets ended in a refund, "
                    "which is at or below the 70% threshold, so this is routed to manual review."
                ),
            )

        # mid / low
        seg_label = "Mid" if segment == "mid" else "Low"
        if not is_first_time and not (ratio is not None and ratio > 0.7):
            return RefundDecision(
                eligible=False,
                rule_label=f"{seg_label} LTV — history below 70%",
                reason=(
                    f"Only {round((ratio or 0) * 100)}% of your past tickets ended in a refund, "
                    "which is at or below the 70% threshold, so this is routed to manual review."
                ),
            )
        if refund_ltv_ratio >= 0.2:
            return RefundDecision(
                eligible=False,
                rule_label=f"{seg_label} LTV — spend cap exceeded",
                reason=(
                    f"Your lifetime refunded coins are {round(refund_ltv_ratio * 100)}% of your "
                    "lifetime coin spend, above the 20% cap, so this is routed to manual review."
                ),
            )
        return RefundDecision(
            eligible=True,
            refund_coins=per_min_charge,
            rule_label=f"{seg_label} LTV — {'first-time user' if is_first_time else 'genuine history'}",
            reason=(
                f"This is your first-ever ticket, so we skip the ticket-history check. Call "
                f"lasted {call.duration_sec}s (under 50s) and you're under the refund spend-cap."
                if is_first_time
                else (
                    f"{round(ratio * 100)}% of your past tickets ended in a refund, call lasted "
                    f"{call.duration_sec}s (under 50s), and you're under the 20% refund spend-cap."
                )
            ),
        )

    # cannot_hear / not_showing_face
    if refund_ltv_ratio < 0.2:
        return RefundDecision(
            eligible=True,
            refund_coins=per_min_charge,
            rule_label="Tech-issue refund rule",
            reason=(
                f"Your lifetime refunded coins are only {round(refund_ltv_ratio * 100)}% of "
                "your lifetime spend (under 20%), so this qualifies for a 1-minute-charge refund."
            ),
        )
    return RefundDecision(
        eligible=False,
        rule_label="Tech-issue refund rule — spend cap exceeded",
        reason=(
            f"Your lifetime refunded coins are {round(refund_ltv_ratio * 100)}% of your "
            "lifetime spend, above the 20% cap. This is routed to manual / Trust & Safety review."
        ),
    )
