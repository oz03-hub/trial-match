"""CMS hospital context: match a trial site to a hospital in data/data.csv.

Precision over recall: a wrong star rating is worse than none. A site matches
only if the city agrees (when known) and its name either contains the CMS name
as a phrase or is a shortened form of it. Ambiguous names match nothing.
"""

import csv
import html
import os
import re
from functools import cache
from pathlib import Path

from app.schemas import Hospital

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOSPITALS_PATH = REPO_ROOT / "data" / "data.csv"

MIN_COVERAGE = 0.6  # a shortened site name must cover this share of the CMS name
STOPWORDS = {"THE", "INC", "LLC", "AND", "OF", "CORP", "CORPORATION"}
ABBREVIATIONS = {
    "ST": "SAINT", "CTR": "CENTER", "CENTRE": "CENTER", "MED": "MEDICAL",
    "HOSP": "HOSPITAL", "MASS": "MASSACHUSETTS", "GEN": "GENERAL",
}


def resolve_hospitals_path() -> Path:
    """HOSPITALS_PATH env var (relative paths resolve against the repo root)."""
    path = Path(os.getenv("HOSPITALS_PATH") or DEFAULT_HOSPITALS_PATH)
    return path if path.is_absolute() else REPO_ROOT / path


def _token(word: str) -> str:
    word = ABBREVIATIONS.get(word, word)
    # crude plural strip so WOMENS/WOMEN and CHILDRENS/CHILDREN agree
    return word[:-1] if len(word) > 3 and word.endswith("S") and not word.endswith("SS") else word


def name_tokens(name: str) -> tuple[str, ...]:
    """'Brigham & Women&#39;s Hosp.' -> ('BRIGHAM', 'WOMEN', 'HOSPITAL')."""
    text = re.sub(r"['’`]", "", html.unescape(name).upper())
    words = re.findall(r"[A-Z0-9]+", text)
    return tuple(_token(w) for w in words if len(w) > 1 and w not in STOPWORDS)


def _normalize_city(city: str) -> str:
    return " ".join(re.findall(r"[A-Z0-9]+", city.upper()))


def _contains_phrase(haystack: tuple[str, ...], needle: tuple[str, ...]) -> bool:
    n = len(needle)
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


class HospitalIndex:
    def __init__(self, rows: list[dict[str, str]]):
        self._entries = []
        for row in rows:
            rating = row["overall_rating"].strip()
            hospital = Hospital(
                name=row["facility_name"].strip(),
                hospital_type=row["hospital_type"].strip(),
                emergency=row["emergency"].strip().lower() == "yes",
                overall_rating=int(rating) if rating.isdigit() else None,
            )
            tokens = name_tokens(hospital.name)
            self._entries.append((hospital, tokens, _normalize_city(row["city"])))

    def match(self, facility: str, city: str) -> Hospital | None:
        site = name_tokens(facility)
        site_city = _normalize_city(city)
        if not site:
            return None
        # Tiers: same words > CMS name as a phrase in the site name > shortened CMS name.
        # Scored across all cities first: if the name best fits a hospital elsewhere
        # ("Baystate Medical Center - Holyoke"), the Holyoke hospital must not win.
        found = []
        for hospital, tokens, hospital_city in self._entries:
            if set(tokens) == set(site):
                tier = 3
            elif _contains_phrase(site, tokens):
                tier = 2
            elif _is_shortened(site, tokens):
                tier = 1
            else:
                continue
            found.append(((tier, len(tokens)), hospital, hospital_city))
        if not found:
            return None
        best = max(score for score, _, _ in found)
        top = [(h, c) for score, h, c in found if score == best]
        if site_city and len(top) > 1:  # tie: the one in the site's city
            top = [(h, c) for h, c in top if c == site_city]
        if len(top) != 1:
            return None  # ambiguous
        hospital, hospital_city = top[0]
        return hospital if not site_city or hospital_city == site_city else None


def _is_shortened(site: tuple[str, ...], tokens: tuple[str, ...]) -> bool:
    """Site name is a subset of the CMS name ("UMass Memorial Medical Center" vs "... UNIVERSITY CAMPUS")."""
    words = set(site)
    return len(words) >= 2 and words <= set(tokens) and len(words) / len(set(tokens)) >= MIN_COVERAGE


@cache
def get_hospitals() -> HospitalIndex:
    """Process-wide index, loaded on first use."""
    with open(resolve_hospitals_path(), newline="", encoding="utf-8") as f:
        return HospitalIndex(list(csv.DictReader(f)))


def match(facility: str, city: str) -> Hospital | None:
    return get_hospitals().match(facility, city)
