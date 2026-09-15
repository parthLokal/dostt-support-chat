"""A per-turn record of which tools ran and whether they succeeded — surfaced
to the frontend as small "Checked your payout status"-style lines above the
reply (see the chatbot PRD's FAQ Answer Generation story), and useful for
debugging/QA without re-reading raw Gemini function-call logs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentTraceStep:
    tool: str
    ok: bool
    summary: str


class AgentTrace:
    def __init__(self) -> None:
        self._steps: list[AgentTraceStep] = []
        self.truncated: bool = False

    def add(self, *, tool: str, ok: bool, summary: str) -> None:
        self._steps.append(AgentTraceStep(tool=tool, ok=ok, summary=summary))

    def to_list(self) -> list[AgentTraceStep]:
        return list(self._steps)
