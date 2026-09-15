"""Pure-data tool definitions. agent/orchestrator.py translates each of these
into a Gemini `types.FunctionDeclaration`. This file stays provider-neutral
and is the ONLY thing agent/orchestrator.py imports from the rest of the
app — never app.integrations or app.services directly (see agent/executor.py
for where those actually get called).

Deliberately no `account_id` property on any of these — the model is told
the account's identity narratively in the system prompt, but has no schema
slot to place an id in. The real enforcement lives in agent/executor.py,
which never trusts a tool call's input for identity anyway; this is defense
in depth, not the enforcement itself.
"""

SEARCH_FAQ = {
    "name": "search_faq",
    "description": (
        "Look up the official Dostt support answer for the account's issue, by describing it "
        "in a short phrase. ALWAYS call this before answering a support question — never "
        "invent an answer yourself. If nothing matches well, it tells you so, and you should "
        "ask the account to describe the issue differently rather than guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A short phrase describing the issue, e.g. 'coins deducted but no call happened'.",
            }
        },
        "required": ["query"],
    },
}

GET_RECENT_CALLS = {
    "name": "get_recent_calls",
    "description": "Get the current account's recent audio/video calls (id, type, duration, coins debited, who it was with, when).",
    "input_schema": {"type": "object", "properties": {}},
}

GET_RECENT_TRANSACTIONS = {
    "name": "get_recent_transactions",
    "description": "Get the current account's recent recharges, withdrawals, or earnings history.",
    "input_schema": {
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "description": "Which kind of transaction to fetch: 'recharge' or 'withdrawal'.",
                "enum": ["recharge", "withdrawal"],
            }
        },
        "required": ["kind"],
    },
}

CREATE_SUPPORT_TICKET = {
    "name": "create_support_ticket",
    "description": (
        "Create a support ticket for an issue you cannot resolve directly — e.g. the account is "
        "still unsatisfied after your answer, the issue is one of the three refund-driven "
        "categories (charged_incorrectly, cannot_hear, not_showing_face), or the FAQ type "
        "requires raising a complaint. For a refund-driven category, ALWAYS pass call_id if you "
        "know it (from get_recent_calls) — our refund-automation rules run automatically the "
        "moment this ticket is created, off the account/call data already on file. You will "
        "NEVER be told whether it was approved; regardless of call_id or outcome, always tell "
        "the account a ticket has been raised and our team will review it and refund them if "
        "genuine — never say or imply a refund has already happened. Always give a real summary "
        "of the underlying issue (not just the account's most recent message) so an admin who "
        "wasn't in this conversation can triage it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "The matched FAQ's id if one applies (e.g. 'charged_incorrectly', "
                    "'negative_balance', 'withdrawal_not_received', 'report_user'), otherwise "
                    "'other'."
                ),
            },
            "sub_category": {
                "type": "string",
                "description": "A short, specific label for the issue, e.g. 'extra coins deducted'.",
            },
            "description": {
                "type": "string",
                "description": (
                    "A summary, in the account's own language, of the actual underlying issue "
                    "across the WHOLE conversation so far — never just their single most recent "
                    "message on its own."
                ),
            },
            "description_en": {
                "type": "string",
                "description": "The same summary as `description`, in clear English, for admins who may not read the account's language.",
            },
            "callback_requested": {
                "type": "boolean",
                "description": "Whether the account said yes when asked if they'd like a callback about this.",
            },
            "call_id": {
                "type": "integer",
                "description": (
                    "The id of the call this is about, from get_recent_calls — REQUIRED for the "
                    "three refund-driven categories whenever you know which call it is, so the "
                    "refund-automation rules can run. Omit for anything else."
                ),
            },
        },
        "required": ["category", "sub_category", "description", "description_en", "callback_requested"],
    },
}

GET_TICKETS = {
    "name": "get_tickets",
    "description": "List the current account's support tickets and their statuses.",
    "input_schema": {"type": "object", "properties": {}},
}

MARK_ISSUE_RESOLVED = {
    "name": "mark_issue_resolved",
    "description": (
        "Call this ONLY after you asked the account something like 'is there anything else I "
        "can help with?' or 'did that solve it?' and they confirmed yes/no more help needed. "
        "Never call this for a FAQ whose feedback type is raise_complaint_only — those always "
        "go through create_support_ticket instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "The matched FAQ's id, or 'other'."},
            "sub_category": {"type": "string", "description": "A short label for the issue."},
        },
        "required": ["category", "sub_category"],
    },
}

# check_refund_eligibility deliberately does not exist as a model-facing tool
# (removed 2026-09-08, was here before): telling the model an eligible/not
# result and trusting it to phrase that faithfully is exactly the kind of
# instruction-following bet this codebase avoids elsewhere (see the ticket
# cap and duplicate-ticket check, both enforced in code, not the prompt).
# The refund-automation rules (app/services/refund_service.py) still run —
# just synchronously inside create_support_ticket
# (app/services/ticket_service.create_ticket_with_automation), which may
# resolve the ticket immediately behind the scenes. The model is never told
# the outcome, so it structurally cannot claim "you've been refunded" —
# every refund-driven case is always presented as "a ticket has been raised
# for review," per product decision (2026-09-08): the PRD's "fewer go to a
# human" intent is preserved on the backend (real automatic resolution,
# same rules), it's just never claimed as an instant fact to the account.
ALL_TOOLS = [
    SEARCH_FAQ,
    GET_RECENT_CALLS,
    GET_RECENT_TRANSACTIONS,
    CREATE_SUPPORT_TICKET,
    GET_TICKETS,
    MARK_ISSUE_RESOLVED,
]
