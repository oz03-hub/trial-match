from app.trials import DEFAULT_DATA_PATH, resolve_data_path


def test_dedup_by_nct_id(store):
    assert sorted(store.trials) == ["NCT00000001", "NCT00000002", "NCT00000003"]


def test_only_recruiting_sites(store):
    sites = store.get("NCT00000001").sites
    assert [s.city for s in sites] == ["Boston", "Worcester", "Boston"]
    assert "Baystate" not in [s.facility for s in sites]
    assert store.get("NCT00000003").sites == []


def test_contact_fallback_to_central(store):
    by_facility = {s.facility: s.contact for s in store.get("NCT00000001").sites}
    assert by_facility["Mass General Hospital"] == "Bob Site, 617-555-0101, bob@mgh.org"
    # blank site contact -> central
    assert by_facility["UMass Memorial"] == "Jane Doe, 617-555-0100, jane@example.org"
    # site lists only a PI (no CONTACT entry) -> central
    assert by_facility["Tufts Medical Center"] == "Jane Doe, 617-555-0100, jane@example.org"
    # neither -> empty
    assert store.get("NCT00000002").sites[0].contact == ""


def test_blank_fields_are_unknown(store):
    t = store.get("NCT00000002")
    assert t.ages == "unknown"
    assert t.phase == "unknown"
    assert t.healthy_volunteers == "unknown"
    t3 = store.get("NCT00000003")
    assert t3.sex == "unknown"
    assert t3.ages == "18 Years and up"
    assert store.get("NCT00000001").phase == "Phase 2"


def test_get_normalizes_id(store):
    assert store.get(" nct00000001 ").nct_id == "NCT00000001"
    assert store.get("NCT99999999") is None


def test_search_and(store):
    out = store.search("type 2 diabetes")
    assert "NCT00000001" in out
    assert "NCT00000002" not in out
    assert "NCT00000003" not in out  # "type" doesn't appear there
    assert store.search("diabetes breast") == "No matching recruiting trials."


def test_search_or(store):
    out = store.search("breast|metformin")
    assert "NCT00000001" in out and "NCT00000002" in out


def test_search_eligibility_ranked_last(store):
    out = store.search("diabetes")
    assert out.index("NCT00000001") < out.index("NCT00000003")


def test_search_block_contents(store):
    out = store.search("metformin")
    assert "Phase 2" in out
    assert "40 Years-75 Years" in out
    assert "3 recruiting sites" in out
    assert "Boston, Worcester" in out


def test_search_limit_and_case(store):
    out = store.search("BOSTON|memory|PET", limit=1)
    assert out.count("NCT0000000") == 1


def test_get_eligibility(store):
    assert "HbA1c between 7.0% and 10.5%" in store.get_eligibility("NCT00000001")
    assert "Ages: 40 Years-75 Years" in store.get_eligibility("NCT00000001")
    assert "No trial" in store.get_eligibility("NCT123")


def test_default_path_relative_to_repo_root(monkeypatch):
    monkeypatch.delenv("DATA_PATH", raising=False)
    assert resolve_data_path() == DEFAULT_DATA_PATH
    assert DEFAULT_DATA_PATH.exists()
    monkeypatch.setenv("DATA_PATH", "data/ma_clinical_trials_recruiting.csv")
    assert resolve_data_path() == DEFAULT_DATA_PATH


def test_site_coordinates(make_store):
    store = make_store(
        {"facility": "A", "city": "Boston", "lat": "42.35843", "lon": "-71.05977"},
        {"facility": "B", "city": "Boston", "lat": "", "lon": ""},
        {"facility": "C", "city": "Boston", "lat": "n/a", "lon": "-71.1"},
    )
    a, b, c = (store.get(f"NCT9000000{i}").sites[0] for i in range(3))
    assert (a.lat, a.lon) == (42.35843, -71.05977)
    assert (b.lat, b.lon) == (None, None)
    assert (c.lat, c.lon) == (None, -71.1)


def test_sites_get_hospital_context(store):
    by_facility = {s.facility: s.hospital for s in store.get("NCT00000001").sites}
    assert by_facility["Mass General Hospital"].overall_rating == 5
    assert by_facility["UMass Memorial"] is None  # "UMass Memorial" alone: too little overlap to trust
    assert by_facility["Tufts Medical Center"] is None  # not a CMS fixture hospital
