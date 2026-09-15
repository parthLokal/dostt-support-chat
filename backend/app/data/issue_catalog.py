"""category -> real production help_and_support_issue.id, for the categories
we've actually confirmed against real data (via the Redash-saved
support-issue-catalog query, id 20282, which lists all 94 real issue rows
as {issue_id, issue_name, category_id}).

Two confirmation tiers, kept distinguishable below because they carry
different risk if wrong:

  - LIVE-TESTED (2026-09-08): our FAQ category string and the real
    issue_name matched exactly AND we actually called the real
    ticket-creation API with that issue_id and confirmed a ticket landed
    (charged_incorrectly/cannot_hear/not_showing_face — tickets 2119-2123).
  - CATALOG-MATCHED (2026-09-11): our FAQ category string matches a real
    issue_name exactly (case aside), found by diffing all 54 FAQ categories
    against the live 94-row catalog, but never actually exercised against
    the real create-ticket endpoint. Exact string match is strong evidence
    (this is exactly how the first three were originally identified, before
    they were also live-tested) but not the same bar — if any of these
    turns out to be wrong, worst case is the real API's own pk-validation
    (confirmed earlier to 400 on an unknown id) rejects it and the mirror
    silently no-ops, same as a category with no id at all. It cannot
    silently misfile a ticket into a real but wrong queue, since a wrong id
    here would have to be a real id for some OTHER real issue_name entirely,
    not just a wrong guess at a number.

Categories not listed here either had no exact match in the real catalog at
all (fuzzy/partial name matches need a human call, not a code guess) or
matched nothing whatsoever — a missing category is a safe, visible no-op
(ticket_service.py's _mirror_to_real_api falls back to local-only), never
silently wrong data.
"""

ISSUE_ID_BY_CATEGORY: dict[str, int] = {
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


def issue_id_for(category: str) -> int | None:
    return ISSUE_ID_BY_CATEGORY.get(category)
