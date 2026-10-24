"""Turn the agent's judgments into the API response.

The LLM only supplies nct_ids, criterion judgments and questions; every fact
(title, phase, sites, contacts, url) comes from the CSV. Invariants the UI
relies on are enforced here rather than trusted to the model.
"""

import re
from difflib import SequenceMatcher

from app.schemas import AgentTrial, AgentTurn, Criterion, Trial, TrialMatchResponse
from app.trials import TrialRecord, TrialStore, get_store

GENERIC_QUESTION = "Ask the study coordinator whether you meet the remaining eligibility criteria."


def _norm(text: str) -> str:
    text = re.sub(r"\\([^\w\s])", r"\1", text)  # CSV has markdown escapes like \<150
    return re.sub(r"\s+", " ", text).strip().lower()


def _tokens(text: str) -> list[str]:
    """Lowercased words/numbers only: punctuation, bullets, quotes and spacing drop out."""
    return re.findall(r"\w+", _norm(text))


MIN_RUN = 3  # shortest run of consecutive words that counts as evidence
MIN_COVERAGE = 0.8  # share of the quote's words that must appear in such runs


def _contains(hay: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return n > 0 and any(hay[i : i + n] == needle for i in range(len(hay) - n + 1))


def quote_in(quote: str, eligibility: str) -> bool:
    """Is the quote in the eligibility text, ignoring case, punctuation and spacing?

    Exact word-for-word match passes. So does a quote that is mostly there: the model
    often trims a word, swaps a symbol for a word, or joins lines with "...". For
    those, at least MIN_COVERAGE of its words must sit in runs of MIN_RUN+ words that
    appear in the text, in order.
    """
    q, hay = _tokens(quote), _tokens(eligibility)
    if not q:
        return False
    if _contains(hay, q):
        return True
    if len(q) < MIN_RUN:
        return False
    blocks = SequenceMatcher(None, q, hay, autojunk=False).get_matching_blocks()
    covered = sum(b.size for b in blocks if b.size >= MIN_RUN)
    return covered / len(q) >= MIN_COVERAGE


def clean_quote(quote: str) -> str:
    """Drop the leading bullet the model often copies along ("* Age 18+")."""
    return re.sub(r"^\s*[*\-•]+\s*", "", quote).strip()


def to_api_trial(agent_trial: AgentTrial, record: TrialRecord) -> Trial:
    return Trial(
        nct_id=record.nct_id,
        title=record.title,
        phase=record.phase,
        conditions=record.conditions,
        summary=record.summary,
        why=agent_trial.why,
        criteria=[
            Criterion(
                text=c.text,
                status=c.status,
                quote=clean_quote(c.quote),
                quote_verified=quote_in(c.quote, record.criteria_text),
            )
            for c in agent_trial.criteria
        ],
        question=(agent_trial.question or "").strip() or None,
        sites=record.sites,
        url=record.url,
    )


def _is_fit(trial: Trial) -> bool:
    return bool(trial.criteria) and all(c.status == "met" for c in trial.criteria)


def normalize(turn: AgentTurn, store: TrialStore | None = None) -> TrialMatchResponse:
    store = store or get_store()
    fit: list[Trial] = []
    closer: list[Trial] = []
    seen: set[str] = set()

    # Fit candidates first so a trial listed in both lists stays a fit.
    candidates = [(t, True) for t in turn.looks_like_a_fit] + [(t, False) for t in turn.worth_a_closer_look]
    for agent_trial, wants_fit in candidates:
        record = store.get(agent_trial.nct_id)
        if record is None or record.nct_id in seen:
            continue
        seen.add(record.nct_id)
        trial = to_api_trial(agent_trial, record)
        if wants_fit and _is_fit(trial):
            trial.question = None
            fit.append(trial)
        else:
            trial.question = trial.question or GENERIC_QUESTION
            closer.append(trial)

    return TrialMatchResponse(
        assistant_message=turn.assistant_message,
        looks_like_a_fit=fit,
        worth_a_closer_look=closer,
        next_question=turn.next_question,
        done=turn.done,
    )
