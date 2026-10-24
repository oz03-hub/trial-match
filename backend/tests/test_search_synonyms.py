def build(make_store):
    return make_store(
        {"brief_title": "Aspirin After Myocardial Infarction", "conditions": "Myocardial Infarction",
         "brief_summary": "Secondary prevention.", "eligibility_criteria": "Age 40+"},
        {"brief_title": "Diabetes and Myocardial Infarction Outcomes", "conditions": "Diabetes",
         "brief_summary": "Both.", "eligibility_criteria": "Age 40+"},
        {"brief_title": "Migraine Prevention", "conditions": "Migraine",
         "brief_summary": "Headaches.", "eligibility_criteria": "Age 18+"},
        {"brief_title": "Hypertension Study", "conditions": "Hypertension",
         "brief_summary": "Blood pressure.", "eligibility_criteria": "Age 30+"},
        {"brief_title": "MI Registry", "conditions": "Cardiac",
         "brief_summary": "Registry (MI) patients.", "eligibility_criteria": "Age 30+"},
    )


def test_lay_phrase_finds_medical_wording(make_store):
    out = build(make_store).search("heart attack")
    assert "NCT90000000" in out and "NCT90000001" in out
    assert "NCT90000002" not in out


def test_and_semantics_across_slots(make_store):
    store = build(make_store)
    out = store.search("heart attack diabetes")
    assert "NCT90000001" in out and "NCT90000000" not in out
    assert store.search("heart attack migraine") == "No matching recruiting trials."


def test_short_synonym_matches_on_word_boundary_only(make_store):
    out = build(make_store).search("heart attack")
    assert "NCT90000004" in out  # "MI" as a word
    assert "NCT90000002" not in out  # "MIgraine" must not match "mi"


def test_high_blood_pressure(make_store):
    out = build(make_store).search("high blood pressure")
    assert "NCT90000003" in out


def test_explicit_or_still_works(make_store):
    out = build(make_store).search("migraine|hypertension")
    assert "NCT90000002" in out and "NCT90000003" in out
