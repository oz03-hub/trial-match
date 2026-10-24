import pytest

from app import hospitals
from app.hospitals import match


def test_csv_parse_handles_quoted_commas():
    h = match("Cooley Dickinson Hospital", "Northampton")
    assert h and h.name == "COOLEY DICKINSON HOSPITAL INC,THE"
    assert h.overall_rating == 2


def test_fields():
    h = match("Massachusetts General Hospital", "Boston")
    assert (h.name, h.hospital_type, h.emergency, h.overall_rating) == (
        "MASSACHUSETTS GENERAL HOSPITAL", "Acute Care Hospitals", True, 5)
    walden = match("Walden Behavioral Care", "Dedham")
    assert walden.emergency is False and walden.overall_rating is None  # "Not Available"
    assert match("Boston Children's Hospital", "Boston").overall_rating is None


@pytest.mark.parametrize("facility", [
    "Massachusetts General Hospital",
    "Mass General Hospital",
    "massachusetts general hospital (MGH)",
    "Massachusetts General Hospital - Site Number : 8400001",
    "Harvard Medical School - Massachusetts General Hospital",
    "The Massachusetts General Hospital, Inc.",
])
def test_matches_variants(facility):
    assert match(facility, "Boston").name == "MASSACHUSETTS GENERAL HOSPITAL"


def test_apostrophes_and_html_entities():
    assert match("Boston Children&#39;s Hospital", "Boston").name == "BOSTON CHILDREN'S HOSPITAL"
    assert match("Boston Childrens Hospital", "Boston").name == "BOSTON CHILDREN'S HOSPITAL"
    assert match("Brigham & Women's Hospital", "Boston").name == "BRIGHAM AND WOMEN'S HOSPITAL"


def test_abbreviations_and_slash_names():
    assert match("UMass Memorial Medical Center - University Campus", "Worcester")
    assert match("Beth Israel Deaconess Med Ctr", "Boston").overall_rating == 3


def test_partial_name_overlap():
    # CMS name has extra words (UNIVERSITY CAMPUS); high token overlap still matches
    assert match("UMass Memorial Medical Center", "Worcester").overall_rating == 3


def test_requires_same_city():
    assert match("Massachusetts General Hospital", "Worcester") is None
    assert match("Massachusetts General Hospital", "boston ").overall_rating == 5  # case/space-insensitive


def test_blank_city_allows_unambiguous_match():
    assert match("Massachusetts General Hospital", "").overall_rating == 5


def test_no_wrong_match_on_shared_words():
    # shares "Medical Center" but is not Holyoke Medical Center
    assert match("Baystate Medical Center - Holyoke", "Holyoke") is None
    assert match("Boston Medical Center", "Boston") is None  # not in the fixture file
    assert match("Boston University", "Boston") is None
    assert match("Massachusetts Institute of Technology", "Cambridge") is None


def test_ambiguous_multi_hospital_name_is_none():
    assert match("Boston Children's Hospital, Brigham & Women's Hospital", "Boston") is None


def test_more_specific_name_wins():
    assert match("Mass General Brigham - Brigham and Women's Hospital - Main Campus", "Boston").overall_rating == 5
    assert match("Mass General Brigham - Brigham and Women's Hospital - Main Campus", "Boston").name.startswith("BRIGHAM")


def test_blank_facility():
    assert match("", "Boston") is None


def test_path_from_env(monkeypatch, tmp_path):
    path = tmp_path / "h.csv"
    path.write_text(
        "facility_id,facility_name,city,county,hospital_type,ownership,emergency,overall_rating\n"
        "1,TINY HOSPITAL,BOSTON,SUFFOLK,Acute Care Hospitals,x,Yes,4\n"
    )
    monkeypatch.setenv("HOSPITALS_PATH", str(path))
    hospitals.get_hospitals.cache_clear()
    assert match("Tiny Hospital", "Boston").overall_rating == 4
    assert match("Massachusetts General Hospital", "Boston") is None


def test_default_path_is_repo_data(monkeypatch):
    monkeypatch.delenv("HOSPITALS_PATH", raising=False)
    assert hospitals.resolve_hospitals_path() == hospitals.DEFAULT_HOSPITALS_PATH
    assert hospitals.DEFAULT_HOSPITALS_PATH.exists()


def test_reordered_name_prefers_exact_words_over_lookalike():
    # same words as BOSTON CHILDREN'S HOSPITAL; must not drift to the Shriners hospital
    assert match("Children's Hospital Boston", "Boston").name == "BOSTON CHILDREN'S HOSPITAL"


def test_network_names_do_not_match_one_member():
    assert match("Mass General Brigham Hospital", "Boston") is None
    assert match("Harvard/Mass General/Brigham Hospitals", "Boston") is None
