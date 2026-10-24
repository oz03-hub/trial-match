"""TrialMatch agent: a tool-calling loop over the local trials CSV.

Ported from the old research agent (lang_chain_agent.py): same `create_agent`
loop and retry/limit middleware, but with local search tools, OpenRouter via
standard chat completions, and structured output (`AgentTurn`) instead of
free text.

CLI: uv run python -m app.agent "I'm 54 with type 2 diabetes in Boston"
"""

import os
import sys
from functools import cache
from typing import NotRequired

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRetryMiddleware,
    ToolCallLimitMiddleware,
    ToolErrorMiddleware,
    ToolRetryMiddleware,
    hook_config,
)
from langchain.agents.structured_output import ToolStrategy
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.prompts import EMPTY_CONVERSATION, FINISH_INSTRUCTION, SYSTEM_PROMPT, language_instruction
from app.schemas import AgentTurn, ChatRequest, TrialMatchResponse
from app.trials import TrialStore, get_store

RECURSION_LIMIT = 500  # graph steps; bounds structured-output validation retries too

FINAL_ANSWER_NUDGE = (
    "You replied with plain text. Reply by calling the AgentTurn tool "
    "(you may call search_trials or get_eligibility first if you still need to)."
)


class FinalAnswerNudgeState(AgentState):
    final_answer_nudges: NotRequired[int]


class FinalAnswerNudgeMiddleware(AgentMiddleware):
    """Send the model back when it ends the loop with plain text.

    ToolStrategy binds tools with tool_choice="any", so a compliant model always
    calls a tool. Some OpenRouter providers ignore tool_choice, though, and a
    plain-text AIMessage ends the loop with no structured response. Nudge it
    back at most `max_nudges` times.
    """

    state_schema = FinalAnswerNudgeState

    def __init__(self, max_nudges: int = 2):
        super().__init__()
        self.max_nudges = max_nudges

    @hook_config(can_jump_to=["model"])
    def after_model(self, state, runtime):
        messages = state.get("messages", [])
        last = messages[-1] if messages else None
        if not isinstance(last, AIMessage) or last.tool_calls:
            return None
        nudges = state.get("final_answer_nudges", 0)
        if nudges >= self.max_nudges:
            return None
        return {
            "messages": [HumanMessage(content=FINAL_ANSWER_NUDGE)],
            "final_answer_nudges": nudges + 1,
            "jump_to": "model",
        }


def make_tools(store: TrialStore):
    @tool
    def search_trials(query: str) -> str:
        """Keyword search over recruiting Massachusetts trials.

        All words must match (AND); use `a|b` inside a word slot for alternatives,
        e.g. "breast cancer|carcinoma". Common lay terms are auto-expanded to medical
        synonyms ("heart attack" also matches "myocardial infarction"). Returns up to
        15 compact trial summaries.
        """
        return store.search(query)

    @tool
    def get_eligibility(nct_id: str) -> str:
        """Full eligibility criteria text for one trial, e.g. "NCT01234567"."""
        return store.get_eligibility(nct_id)

    return [search_trials, get_eligibility]


def build_model() -> ChatOpenAI:
    """OpenRouter over standard chat completions."""
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "openai/gpt-6-luna"),
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        temperature=0.2,
        timeout=90,
        max_retries=0,  # ModelRetryMiddleware is the only retry layer
    )


def build_agent(
    model: BaseChatModel | None = None,
    store: TrialStore | None = None,
    search_limit: int = 8,
    eligibility_limit: int = 16,
):
    store = store or get_store()
    return create_agent(
        model=model or build_model(),
        tools=make_tools(store),
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(AgentTurn, tool_message_content="Reply recorded."),
        middleware=[
            # Raise after retries instead of fabricating an error-string answer;
            # the API turns the exception into a friendly error response.
            ModelRetryMiddleware(max_retries=2, on_failure="error"),
            # First in list = outermost: ToolError catches what ToolRetry re-raises.
            ToolErrorMiddleware(
                on_error=lambda exc, req: f"{req.tool_call['name']} failed ({exc}). Try different input."
            ),
            ToolRetryMiddleware(max_retries=1, on_failure="error", initial_delay=0.2),
            # Per-tool limits, so the final AgentTurn call is never blocked.
            # "continue" returns an error to the model, which then must answer.
            ToolCallLimitMiddleware(tool_name="search_trials", run_limit=search_limit),
            ToolCallLimitMiddleware(tool_name="get_eligibility", run_limit=eligibility_limit),
            FinalAnswerNudgeMiddleware(),
        ],
    )


@cache
def default_agent():
    return build_agent()


def summarize_previous(previous: TrialMatchResponse) -> str:
    """Compact view of last turn's lists so the agent updates rather than restarts."""
    lines = []
    for label, trials in [("looks_like_a_fit", previous.looks_like_a_fit),
                          ("worth_a_closer_look", previous.worth_a_closer_look)]:
        if not trials:
            continue
        lines.append(f"{label}:")
        for t in trials:
            lines.append(f"- {t.nct_id} ({t.title}) why: {t.why}")
            for c in t.criteria:
                lines.append(f"  - [{c.status}] {c.text} | quote: \"{c.quote}\"")
            if t.question:
                lines.append(f"  - open question: {t.question}")
    if previous.next_question:
        lines.append(f"Last question you asked the user: {previous.next_question.text}")
    if not lines:
        return ""
    return "Your previous results (update these, don't start over):\n" + "\n".join(lines)


def build_messages(request: ChatRequest) -> list[dict]:
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    notes = []
    if request.previous:
        notes.append(summarize_previous(request.previous))
    if request.finish:
        notes.append(FINISH_INSTRUCTION)
    notes = [n for n in notes if n]
    if not notes and (not messages or messages[-1]["role"] != "user"):
        messages.append({"role": "user", "content": EMPTY_CONVERSATION})
    notes.append(language_instruction(request.language, request.plain_language))
    notes = [n for n in notes if n]
    if notes:
        messages.append({"role": "user", "content": "[TrialMatch app note]\n" + "\n\n".join(notes)})
    return messages


def run_turn(request: ChatRequest, agent=None) -> AgentTurn:
    agent = agent or default_agent()
    result = agent.invoke(
        {"messages": build_messages(request)},
        config={"recursion_limit": RECURSION_LIMIT},
    )
    turn = result.get("structured_response")
    if turn is None:
        raise RuntimeError("Agent finished without a structured reply.")
    return turn


if __name__ == "__main__":
    from dotenv import load_dotenv

    from app.service import normalize
    from app.trials import REPO_ROOT

    load_dotenv(REPO_ROOT / ".env")
    text = " ".join(sys.argv[1:]) or "I'm 54 with type 2 diabetes in Boston"
    turn = run_turn(ChatRequest(messages=[{"role": "user", "content": text}]))
    print(normalize(turn).model_dump_json(indent=2))
