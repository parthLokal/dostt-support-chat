"""Maps tool names to handlers. Only agent/executor.py resolves a handler
here — the orchestrator only ever sees agent/tool_schemas.py (pure data).

Each handler receives `(tool_input, ctx)`. Handlers must use `ctx.account_id`
for identity, never anything out of tool_input — see agent/executor.py for
the enforcement.
"""

from dataclasses import dataclass, field
from typing import Callable

from app.agent.context import SessionContext
from app.core.time import is_within_business_hours
from app.integrations import call_client, transaction_client
from app.schemas.ticket import TicketRead
from app.services import chat_session_service, faq_service, ticket_service


@dataclass(frozen=True)
class ToolResult:
    content_for_model: str
    summary_for_trace: str
    is_error: bool = False
    # Out-of-band data the API layer surfaces to the frontend (e.g. a newly
    # created ticket's id, or a flag to show the feedback widget) — never
    # seen by the model itself, only read by chat_service/routes.
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[[dict, SessionContext], ToolResult]


def _handle_search_faq(tool_input: dict, ctx: SessionContext) -> ToolResult:
    query = tool_input.get("query", "")
    faq = faq_service.search(query, audience=ctx.role)
    if faq is None:
        return ToolResult(
            content_for_model="no_match=true (no FAQ matched well — ask the account to describe the issue differently, don't invent an answer)",
            summary_for_trace=f"Searched FAQs for '{query}' — no match",
        )
    content = (
        f"faq_id={faq.id} category=\"{faq.category}\" official_answer=\"{faq.answer}\" "
        f"feedback_type={faq.feedback} refund_driven={faq.refund_driven} "
        "(rewrite official_answer conversationally in the account's language, but preserve every "
        "fact, number, amount, and condition in it exactly)"
    )
    return ToolResult(content_for_model=content, summary_for_trace=f"Looked up the FAQ for '{query}'")


def _handle_get_recent_calls(tool_input: dict, ctx: SessionContext) -> ToolResult:
    calls = call_client.get_recent_calls(ctx.db, ctx.account_id)
    if not calls:
        return ToolResult(content_for_model="no_recent_calls=true", summary_for_trace="Checked your recent calls — none found")
    rendered = [
        f"call_id={c.id} type={c.call_type} duration_sec={c.duration_sec} coins_debited={c.coins_debited} with={c.counterpart_name}"
        for c in calls
    ]
    return ToolResult(content_for_model=" | ".join(rendered), summary_for_trace="Checked your recent calls")


def _handle_get_recent_transactions(tool_input: dict, ctx: SessionContext) -> ToolResult:
    kind = tool_input.get("kind", "recharge")
    txs = transaction_client.get_recent_transactions(ctx.db, ctx.account_id, kind)
    if not txs:
        return ToolResult(content_for_model="no_recent_transactions=true", summary_for_trace=f"Checked your recent {kind}s — none found")
    rendered = [
        f"transaction_id={t.id} amount_inr={t.amount_inr} coins={t.coins} status={t.status}" for t in txs
    ]
    return ToolResult(content_for_model=" | ".join(rendered), summary_for_trace=f"Checked your recent {kind}s")


def _handle_create_support_ticket(tool_input: dict, ctx: SessionContext) -> ToolResult:
    if ctx.ticket_count_this_session >= ticket_service.MAX_TICKETS_PER_SESSION:
        return ToolResult(
            content_for_model=(
                "error: this session has already reached the 2-ticket limit — tell the "
                "account they've reached the limit for this chat and to check back on their "
                "existing tickets, or reach out again a little later."
            ),
            summary_for_trace="Ticket limit reached for this session",
            is_error=True,
        )

    category = tool_input.get("category", "other")
    existing = ticket_service.get_active_ticket_for_category(ctx.db, ctx.account_id, category)
    if existing is not None:
        return ToolResult(
            content_for_model=(
                f"error: account already has an active ticket for this — ticket #{existing.id}. "
                "Do NOT create another one. Tell them this issue is already being worked on and "
                "they can check its status in My Tickets — never mention its internal status or "
                "whether it was approved either way."
            ),
            summary_for_trace="Already has an active ticket for this — didn't raise a duplicate",
            is_error=True,
        )

    # For the three refund-driven categories, this runs the v1.1 refund rules
    # synchronously and may resolve the ticket immediately — see
    # ticket_service.create_ticket_with_automation's docstring. The outcome
    # is deliberately never read back here: content_for_model below never
    # varies with it, so there is no path by which the model could learn or
    # repeat an eligible/not-eligible verdict to the account.
    ticket = ticket_service.create_ticket_with_automation(
        ctx.db,
        account_id=ctx.account_id,
        category=category,
        sub_category=tool_input.get("sub_category", "general"),
        description=tool_input.get("description", ""),
        description_en=tool_input.get("description_en", ""),
        call_id=tool_input.get("call_id"),
        callback_requested=bool(tool_input.get("callback_requested", False)),
        auth_token=ctx.auth_token,
        language_id=ctx.language_id,
        user_type_code=ctx.user_type_code,
        country_code=ctx.country_code,
        app_version=ctx.app_version,
        session_id=ctx.session_id,
    )
    chat_session_service.mark_escalated(ctx.db, ctx.session_id, ticket_id=ticket.id, category=category)

    business_hours_note = "" if is_within_business_hours() else (
        " note_outside_business_hours=true (mention that since it's currently outside "
        "business hours, 9 AM-7 PM IST, a callback would happen the next business day)"
    )
    attachment_note = (
        " attachment_included=true (you may mention their screenshot was attached to the ticket)"
        if ticket.attachment_path else ""
    )
    content = (
        f"ticket_id={ticket.id} status=submitted_for_review{business_hours_note}{attachment_note} "
        "(ALWAYS tell the account a ticket has been raised and our team will review it and "
        "refund them if genuine, when relevant — NEVER state or imply whether it was approved, "
        "rejected, or already refunded, even if you think you know; you do not actually know)"
    )
    return ToolResult(
        content_for_model=content,
        summary_for_trace=f"Raised ticket #{ticket.id} for review",
        metadata={"created_ticket_id": ticket.id, "show_feedback": True},
    )


def _handle_get_tickets(tool_input: dict, ctx: SessionContext) -> ToolResult:
    tickets = ticket_service.list_tickets_for_account(ctx.db, ctx.account_id)
    rendered = [TicketRead.model_validate(t).model_dump_json() for t in tickets]
    return ToolResult(content_for_model=str(rendered), summary_for_trace="Looked up your tickets")


def _handle_mark_issue_resolved(tool_input: dict, ctx: SessionContext) -> ToolResult:
    category = tool_input.get("category", "other")
    sub_category = tool_input.get("sub_category", "general")
    chat_session_service.mark_resolved_by_bot(ctx.db, ctx.session_id, category=category, sub_category=sub_category)
    return ToolResult(
        content_for_model="ok",
        summary_for_trace="Marked this issue as resolved",
        metadata={"show_feedback": True},
    )


REGISTRY: dict[str, ToolSpec] = {
    spec.name: spec
    for spec in [
        ToolSpec("search_faq", _handle_search_faq),
        ToolSpec("get_recent_calls", _handle_get_recent_calls),
        ToolSpec("get_recent_transactions", _handle_get_recent_transactions),
        ToolSpec("create_support_ticket", _handle_create_support_ticket),
        ToolSpec("get_tickets", _handle_get_tickets),
        ToolSpec("mark_issue_resolved", _handle_mark_issue_resolved),
    ]
}
