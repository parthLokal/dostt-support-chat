"""Drives the tool-calling loop against a FakeAgentClient — no real Gemini
access needed, since AgentClient is a narrow Protocol (agent/client.py)
exactly so this swap is possible.
"""

from google.genai import types

from app.agent import orchestrator
from app.agent.context import SessionContext


class FakeAgentClient:
    def __init__(self, responses: list[types.GenerateContentResponse]) -> None:
        self._responses = list(responses)

    def generate(self, *, system, contents, tools) -> types.GenerateContentResponse:
        return self._responses.pop(0)


def _text_response(text: str, finish_reason=types.FinishReason.STOP) -> types.GenerateContentResponse:
    candidate = types.Candidate(
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        finish_reason=finish_reason,
    )
    return types.GenerateContentResponse(candidates=[candidate])


def _function_call_response(name: str, args: dict) -> types.GenerateContentResponse:
    candidate = types.Candidate(
        content=types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
        ),
        finish_reason=types.FinishReason.STOP,
    )
    return types.GenerateContentResponse(candidates=[candidate])


def _ctx(db, account_id) -> SessionContext:
    return SessionContext(account_id=account_id, name="Priya", role="user", language="en", db=db, session_id="s1")


def test_final_text_reply_with_no_tool_calls(db, account):
    client = FakeAgentClient([_text_response("Hi there, how can I help?")])
    result = orchestrator.run_chat_turn(client, _ctx(db, account.id), "hello")
    assert result.reply == "Hi there, how can I help?"
    assert result.trace == []


def test_tool_call_then_final_reply_builds_a_trace(db, account):
    client = FakeAgentClient([
        _function_call_response("search_faq", {"query": "negative balance"}),
        _text_response("I found the answer for you."),
    ])
    result = orchestrator.run_chat_turn(client, _ctx(db, account.id), "my wallet is negative")
    assert result.reply == "I found the answer for you."
    assert len(result.trace) == 1
    assert result.trace[0].tool == "search_faq"
    assert result.trace[0].ok


def test_unusable_response_retried_then_falls_back_to_apology(db, account):
    unusable = types.GenerateContentResponse(
        candidates=[types.Candidate(content=None, finish_reason=types.FinishReason.MALFORMED_FUNCTION_CALL)]
    )
    client = FakeAgentClient([unusable] * orchestrator._MAX_GENERATE_ATTEMPTS)
    result = orchestrator.run_chat_turn(client, _ctx(db, account.id), "hello")
    assert result.reply == orchestrator._APOLOGY_REPLY
