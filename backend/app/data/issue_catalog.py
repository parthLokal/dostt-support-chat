"""category -> real help_and_support_issue.id, split by environment because
staging and production are NOT the same dataset — confirmed empirically
2026-09-15 by pulling both catalogs directly and diffing them: staging has
49 issues total, production has 94, and the same real-world concept can
have a completely different id in each (e.g. "Not Getting Calls" is id 43
on staging, id 363 on production). Using the wrong environment's id doesn't
silently misfile a ticket — the real API's own pk-validation 400s on an
unknown id (confirmed via a real "Invalid pk 361 - object does not exist"
response when a production-only id was sent to staging) — but it does mean
the mirror silently no-ops for that ticket, same as having no id at all.

issue_id_for() picks the right dict based on which DOSTT_API_BASE_URL is
actually configured, so this never needs a manual environment flag that
could drift out of sync with the setting that actually matters.
"""

from app.core.config import settings

# --- Production ---
# Sourced via the Redash-saved support-issue-catalog query (id 20282, all 94
# real production rows as {issue_id, issue_name, category_id} — BigQuery
# only has production data replicated into it, no staging equivalent).
#
# Two confirmation tiers, kept distinguishable because they carry different
# risk if wrong:
#   - LIVE-TESTED (2026-09-08): FAQ category string and real issue_name
#     matched exactly AND the real ticket-creation API was actually called
#     with that issue_id and confirmed a ticket landed (charged_incorrectly/
#     cannot_hear/not_showing_face — tickets 2119-2123).
#   - CATALOG-MATCHED (2026-09-11): exact issue_name string match (case
#     aside) against the live 94-row catalog, never actually exercised
#     against the real create-ticket endpoint.
ISSUE_ID_BY_CATEGORY_PRODUCTION: dict[str, int] = {
    # --- Live-tested (2026-09-08): real ticket actually created and confirmed ---
    "charged_incorrectly": 361,  # "Charged Incorrectly for Call"
    "cannot_hear": 463,  # "Cannot Hear Dostt's Voice"
    "not_showing_face": 362,  # "Dostt Not Showing Face"
    # --- Catalog-matched (2026-09-11): exact issue_name match, not yet live-tested ---
    "preferred_listener": 357,  # "Favourite Listener Unavailable"
    "no_listener_online": 356,  # "No Listener Online"
    "not_getting_calls": 363,  # "Not Getting Calls"
    "recharge_not_added": 360,  # "Recharged but Coins Not Added"
    "recharge_twice": 465,  # "Recharged Twice by Mistake"
    "negative_balance": 337,  # "Wallet Balance is Negative"
    "withdrawal_not_received": 336,  # "Withdrawal Amount Not Received"
    "tds_help": 265,  # "TDS Deduction Help"
    "earnings_mismatch": 529,  # "Earning Not Matching With Call Duration"
    "kyc_limit_exceeded": 497,  # "KYC Limit Exceeded"
    "pan_delink_transfer": 334,  # "PAN Delink and Link to Other Account"
    "change_language": 367,  # "Change Language"
    "multiple_languages_request": 234,  # "Add One More Language"
    "access_request": 596,  # "SDT Access Request"
    "delete_call_history": 348,  # "Delete Call History"
    "report_user": 464,  # "Inappropriate Behaviour"
    "personal_info_request": 430,  # "Asking for Personal Info"
}

# --- Staging ---
# Sourced directly from the real API itself (2026-09-15): GET
# {DOSTT_API_BASE_URL}/help-and-support/categories/ returns the live
# staging issue catalog — self-serve, no Redash/DB access needed (Redash
# only ever had production data). Only exact/clear title matches included
# here — staging's data is noticeably messier than production's (duplicate
# ids listed under multiple category groups, typos like "1What is
# competition", "exp p block"), so ~10 more FAQ categories had plausible
# but not certain staging matches, deliberately left out rather than
# guessed (same policy as production's fuzzy-match exclusions above).
# None of these have been live-tested against a real create-ticket call
# yet (unlike the three production ones) — exact title match only.
ISSUE_ID_BY_CATEGORY_STAGING: dict[str, int] = {
    "not_getting_calls": 43,  # "Not getting calls ?"
    "recharge_not_added": 39,  # "Recharged but coins not added ?"
    "negative_balance": 58,  # "Why is my account balance negative ?"
    "tds_help": 77,  # "What is TDS and how much TDS is deducted for me ?"
    "change_language": 37,  # "Change my language"
    "delete_call_history": 48,  # "How do I delete my call History"
    "report_user": 60,  # "What to do if user is behaving inappropriately ?"
    "personal_info_request": 54,  # "What should I do if a Listener asks for my personal information ?"
    "not_showing_face": 55,  # "...not showing their face on a video call ?"
    "cannot_hear": 106,  # "call voice not clear"
}


def _is_staging_base_url() -> bool:
    return "testdostt" in settings.DOSTT_API_BASE_URL


def issue_id_for(category: str) -> int | None:
    catalog = ISSUE_ID_BY_CATEGORY_STAGING if _is_staging_base_url() else ISSUE_ID_BY_CATEGORY_PRODUCTION
    return catalog.get(category)
