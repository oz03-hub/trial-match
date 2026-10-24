"""Report-time LLM call: patient-voice outreach message bodies, one per listed trial.

A fresh model call, separate from the agent conversation. The LLM writes only the
body; greeting, subject, sign-off and the footer are added in code (report.py).
It never raises: on any failure it returns what it has and the report falls back
to a deterministic template for the missing trials.
"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent import build_model
from app.prompts import OUTREACH_PROMPT
from app.schemas import ChatMessage, OutreachEmails, Trial, TrialMatchResponse

log = logging.getLogger("trialmatch")


def all_trials(response: TrialMatchResponse) -> list[Trial]:
    return [*response.looks_like_a_fit, *response.worth_a_closer_look]


def build_outreach_input(messages: list[ChatMessage], trials: list[Trial]) -> str:
    said = [m.content.strip() for m in messages if m.role == "user" and m.content.strip()]
    lines = ["What the patient said (their own words):"]
    lines += [f"- {s}" for s in said] or ["- (nothing)"]
    for t in trials:
        lines += ["", f"Trial {t.nct_id}: {t.title}"]
        for c in t.criteria:
            lines.append(f"- [{c.status}] {c.text}" + (f' | quote: "{c.quote}"' if c.quote else ""))
    return "\n".join(lines)


def generate_emails(
    messages: list[ChatMessage],
    response: TrialMatchResponse,
    model: BaseChatModel | None = None,
) -> dict[str, str]:
    """{nct_id: body} for the listed trials. Unknown ids are dropped; {} on failure."""
    trials = all_trials(response)
    if not trials:
        return {}
    try:
        llm = (model or build_model()).with_structured_output(OutreachEmails, method="function_calling")
        result = llm.invoke([
            SystemMessage(content=OUTREACH_PROMPT),
            HumanMessage(content=build_outreach_input(messages, trials)),
        ])
        if not isinstance(result, OutreachEmails):
            return {}
        listed = {t.nct_id for t in trials}
        bodies: dict[str, str] = {}
        for e in result.emails:
            nct = e.nct_id.strip().upper()
            if nct in listed and nct not in bodies and e.body.strip():
                bodies[nct] = e.body
        return bodies
    except Exception:
        log.exception("outreach email generation failed; using fallback template")
        return {}
