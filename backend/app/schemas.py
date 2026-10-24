"""Wire contract between the agent, the API and the browser.

Two layers:
- `Agent*` models are what the LLM fills in (judgments only, no facts).
- `Trial` / `TrialMatchResponse` are what the API returns: agent judgments
  enriched with facts (title, phase, sites, contacts, url) from the CSV.
"""

from typing import Literal

from pydantic import BaseModel, Field

CriterionStatus = Literal["met", "unmet", "unknown"]


# ---- What the LLM produces -------------------------------------------------


class AgentCriterion(BaseModel):
    text: str = Field(description="Plain-language criterion, e.g. 'Age 18-75'.")
    status: CriterionStatus
    quote: str = Field(
        description="Exact line copied from the trial's eligibility criteria."
    )


class AgentTrial(BaseModel):
    nct_id: str
    why: str = Field(description="One sentence: why this trial is relevant.")
    criteria: list[AgentCriterion]
    question: str | None = Field(
        default=None,
        description="For 'worth a closer look': the question that would resolve it.",
    )


class NextQuestion(BaseModel):
    text: str = Field(description="The one question to ask. Don't also ask it in assistant_message.")
    suggested_answers: list[str] = Field(
        min_length=2,
        description="2-5 short tappable answers (1-4 words each); include 'Not sure' when it fits.",
    )


class AgentTurn(BaseModel):
    """Structured reply for one conversation turn."""

    assistant_message: str = Field(description="2-4 sentences on what changed. No questions here.")
    looks_like_a_fit: list[AgentTrial]
    worth_a_closer_look: list[AgentTrial]
    # Required (no default) so the model can't silently skip it; null only when done.
    next_question: NextQuestion | None = Field(
        description="Required every turn unless done=true. Null only when done=true."
    )
    done: bool = False


class OutreachEmail(BaseModel):
    nct_id: str = Field(description="Exact NCT id of the trial this message is for.")
    body: str = Field(
        description="Patient-voice message body in English, ~80-150 words. "
        "No greeting, subject line or sign-off."
    )


class OutreachEmails(BaseModel):
    """Report-time LLM output: one outreach message body per listed trial."""

    emails: list[OutreachEmail]


# ---- What the API returns ---------------------------------------------------


class Criterion(BaseModel):
    text: str
    status: CriterionStatus
    quote: str
    quote_verified: bool = False


class Hospital(BaseModel):
    """CMS hospital rating (data/data.csv) matched to a trial site by name."""

    name: str
    hospital_type: str
    emergency: bool
    overall_rating: int | None  # 1-5 stars; None = "Not Available"


class Site(BaseModel):
    facility: str
    city: str
    zip: str
    contact: str  # site_contacts, falling back to central_contacts
    lat: float | None = None
    lon: float | None = None
    hospital: Hospital | None = None


class Trial(BaseModel):
    nct_id: str
    title: str
    phase: str
    conditions: str
    summary: str
    why: str
    criteria: list[Criterion]
    question: str | None = None
    sites: list[Site]
    url: str


class TrialMatchResponse(BaseModel):
    assistant_message: str
    looks_like_a_fit: list[Trial] = []
    worth_a_closer_look: list[Trial] = []
    next_question: NextQuestion | None = None
    done: bool = False
    final_report_markdown: str | None = None
    error: bool = False


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    previous: TrialMatchResponse | None = None
    finish: bool = False
    language: Literal["en", "es", "pt", "zh", "ht", "vi"] = "en"
    plain_language: bool = False  # ~6th-grade reading level
