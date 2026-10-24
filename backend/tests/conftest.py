import csv
from pathlib import Path

import pytest

from app import hospitals
from app.trials import TrialStore

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_CSV = FIXTURES / "trials.csv"
HOSPITALS_CSV = FIXTURES / "hospitals.csv"

TRIAL_COLUMNS = [
    "nct_id", "brief_title", "overall_status", "conditions", "phases", "min_age", "max_age",
    "sex", "healthy_volunteers", "central_contacts", "facility", "city", "state", "zip",
    "site_status", "lat", "lon", "site_contacts", "brief_summary", "eligibility_criteria", "url",
]


@pytest.fixture(autouse=True)
def fixture_hospitals(monkeypatch):
    """Tests use a tiny hospitals CSV, not the real CMS file."""
    monkeypatch.setenv("HOSPITALS_PATH", str(HOSPITALS_CSV))
    hospitals.get_hospitals.cache_clear()
    yield
    hospitals.get_hospitals.cache_clear()


@pytest.fixture
def store() -> TrialStore:
    return TrialStore.from_csv(FIXTURE_CSV)


@pytest.fixture
def make_store(tmp_path):
    """Build a TrialStore from row dicts; unspecified columns default to blank/RECRUITING."""

    def build(*rows: dict) -> TrialStore:
        path = tmp_path / "trials.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, TRIAL_COLUMNS)
            writer.writeheader()
            for i, row in enumerate(rows):
                writer.writerow({
                    "nct_id": f"NCT9000000{i}", "brief_title": "t", "site_status": "RECRUITING",
                    **row,
                })
        return TrialStore.from_csv(path)

    return build
