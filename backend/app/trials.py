"""Trial data access: load the MA trials CSV, dedupe by trial, keyword search.

The CSV has one row per (trial x site). We group rows by nct_id, keep only
RECRUITING sites, and give each site a contact (site contact, falling back to
the trial's central contact). Blank age/sex fields mean "unknown", never a
hard filter.
"""

import csv
import os
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from app import hospitals
from app.schemas import Site
from app.synonyms import expand_query

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = REPO_ROOT / "data" / "ma_clinical_trials_recruiting.csv"
SHORT_TERM = 3  # terms this short must match whole words ("mi" is not "migraine")


def resolve_data_path() -> Path:
    """DATA_PATH env var (relative paths resolve against the repo root)."""
    path = Path(os.getenv("DATA_PATH") or DEFAULT_DATA_PATH)
    return path if path.is_absolute() else REPO_ROOT / path


def study_url(nct_id: str) -> str:
    return f"https://clinicaltrials.gov/study/{nct_id}"


def _contact(raw: str) -> str:
    """'Name; CONTACT; phone; email | Name; PRINCIPAL_INVESTIGATOR' -> 'Name, phone, email'.

    Only CONTACT entries count; a bare PI name isn't someone you can reach.
    """
    contacts = []
    for entry in raw.split("|"):
        parts = [p.strip() for p in entry.split(";") if p.strip()]
        if len(parts) >= 2 and parts[1] == "CONTACT":
            contacts.append(", ".join([parts[0], *parts[2:]]))
    return " | ".join(contacts)


def _phase(raw: str) -> str:
    if not raw:
        return "unknown"
    if raw == "NA":
        return "N/A"
    return " / ".join(p.strip().replace("PHASE", "Phase ").replace("EARLY_", "Early ")
                      for p in raw.split(";"))


def _ages(min_age: str, max_age: str) -> str:
    if min_age and max_age:
        return f"{min_age}-{max_age}"
    if min_age:
        return f"{min_age} and up"
    if max_age:
        return f"up to {max_age}"
    return "unknown"


@dataclass
class TrialRecord:
    nct_id: str
    title: str
    conditions: str
    phase: str
    ages: str
    sex: str
    healthy_volunteers: str
    central_contact: str
    summary: str
    eligibility: str
    url: str
    sites: list[Site] = field(default_factory=list)

    @property
    def criteria_text(self) -> str:
        """Structured fields + eligibility text: what the agent reads and quotes from."""
        return "\n".join([
            f"Ages: {self.ages}",
            f"Sex: {self.sex}",
            f"Healthy volunteers: {self.healthy_volunteers}",
            "",
            self.eligibility,
        ])

    def block(self) -> str:
        """Compact text block shown to the agent in search results."""
        cities = ", ".join(dict.fromkeys(s.city for s in self.sites)) or "none"
        return "\n".join([
            f"[{self.nct_id}] {self.title}",
            f"  conditions: {self.conditions[:200]}",
            f"  phase: {self.phase} | ages: {self.ages} | sex: {self.sex}"
            f" | healthy volunteers: {self.healthy_volunteers}",
            f"  {len(self.sites)} recruiting sites: {cities}",
        ])


def _record(row: dict[str, str]) -> TrialRecord:
    return TrialRecord(
        nct_id=row["nct_id"],
        title=row["brief_title"],
        conditions=row["conditions"],
        phase=_phase(row["phases"]),
        ages=_ages(row["min_age"], row["max_age"]),
        sex=row["sex"].lower() or "unknown",
        healthy_volunteers={"True": "yes", "False": "no"}.get(row["healthy_volunteers"], "unknown"),
        central_contact=_contact(row["central_contacts"]),
        summary=row["brief_summary"],
        eligibility=row["eligibility_criteria"],
        url=study_url(row["nct_id"]),
    )


@cache
def _word_pattern(alt: str) -> re.Pattern:
    return re.compile(rf"(?<![a-z0-9]){re.escape(alt)}(?![a-z0-9])")


def _matches(term: str, text: str) -> bool:
    """Any `|` alternative in the text; short ones (<= 3 chars) only as whole words."""
    return any(
        alt and (_word_pattern(alt).search(text) if len(alt) <= SHORT_TERM else alt in text)
        for alt in term.split("|")
    )


def _float(raw: str) -> float | None:
    try:
        return float(raw)
    except ValueError:
        return None


class TrialStore:
    def __init__(self, trials: dict[str, TrialRecord]):
        self.trials = trials
        # Lowercased search text, precomputed once.
        self._primary = {k: f"{t.title}\n{t.conditions}\n{t.summary}".lower() for k, t in trials.items()}
        self._secondary = {k: t.eligibility.lower() for k, t in trials.items()}

    @classmethod
    def from_csv(cls, path: Path | str) -> "TrialStore":
        trials: dict[str, TrialRecord] = {}
        seen_sites: set[tuple[str, str, str]] = set()
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                trial = trials.get(row["nct_id"]) or trials.setdefault(row["nct_id"], _record(row))
                key = (trial.nct_id, row["facility"], row["city"])
                if row["site_status"] != "RECRUITING" or key in seen_sites:
                    continue
                seen_sites.add(key)
                trial.sites.append(Site(
                    facility=row["facility"],
                    city=row["city"],
                    zip=row["zip"],
                    contact=_contact(row["site_contacts"]) or trial.central_contact,
                    lat=_float(row["lat"]),
                    lon=_float(row["lon"]),
                    hospital=hospitals.match(row["facility"], row["city"]),
                ))
        return cls(trials)

    def get(self, nct_id: str) -> TrialRecord | None:
        return self.trials.get(nct_id.strip().upper())

    def search(self, query: str, limit: int = 15) -> str:
        """All whitespace-separated terms must match (AND); 'a|b' matches either.

        Common lay terms are expanded first ("heart attack" also finds "myocardial
        infarction"); see app/synonyms.py.

        Ranking: matches in title/conditions/summary first (more terms in the
        title/conditions = higher, trials with recruiting sites first), then eligibility-only matches.
        """
        terms = expand_query(query)
        if not terms:
            return "Empty query."
        primary, secondary = [], []
        for nct_id, text in self._primary.items():
            if all(_matches(t, text) for t in terms):
                primary.append(nct_id)
            elif all(_matches(t, text + "\n" + self._secondary[nct_id]) for t in terms):
                secondary.append(nct_id)

        def rank(nct_id: str) -> tuple[int, bool]:
            t = self.trials[nct_id]
            head = f"{t.title}\n{t.conditions}".lower()
            return sum(_matches(term, head) for term in terms), bool(t.sites)

        primary.sort(key=rank, reverse=True)
        hits = (primary + secondary)[:limit]
        if not hits:
            return "No matching recruiting trials."
        total = len(primary) + len(secondary)
        header = f"{total} trials matched; showing {len(hits)}."
        return "\n\n".join([header, *(self.trials[h].block() for h in hits)])

    def get_eligibility(self, nct_id: str) -> str:
        trial = self.get(nct_id)
        if trial is None:
            return f"No trial with id {nct_id!r}. Use an nct_id from search results."
        return f"[{trial.nct_id}] {trial.title}\n\n{trial.criteria_text}"


@cache
def get_store() -> TrialStore:
    """Process-wide store, loaded on first use."""
    return TrialStore.from_csv(resolve_data_path())
