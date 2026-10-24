from app.synonyms import expand_query


def slots(query):
    return [set(slot.split("|")) for slot in expand_query(query)]


def test_lay_term_expands_to_medical_terms():
    (slot,) = slots("hypertension")
    assert {"hypertension", "hypertensive"} <= slot
    (slot,) = slots("cancer")
    assert {"cancer", "carcinoma", "tumor", "neoplasm", "malignan"} <= slot


def test_multiword_phrase_is_one_slot():
    (slot,) = slots("heart attack")
    assert {"heart attack", "myocardial infarction", "mi"} <= slot
    (slot,) = slots("high blood pressure")
    assert "hypertension" in slot


def test_unknown_terms_pass_through_and_slots_stay_anded():
    result = slots("type 2 diabetes")
    assert result[0] == {"type"} and result[1] == {"2"}
    assert {"diabetes", "diabetic", "t2d"} <= result[2]
    assert len(slots("breast cancer")) == 2


def test_user_alternatives_are_kept_and_expanded():
    (slot,) = slots("cancer|leukemia")
    assert {"leukemia", "carcinoma", "cancer"} <= slot


def test_possessive_and_plural_forms():
    assert "dementia" in slots("alzheimer's")[0]
    assert "dementia" in slots("Alzheimers")[0]
    assert "myocardial infarction" in slots("Heart Attacks")[0]


def test_case_and_punctuation_and_empty():
    assert "hypertension" in slots("High Blood Pressure?")[0]
    assert expand_query("   ") == []


def test_no_pipes_leak_inside_alternatives():
    for slot in expand_query("heart attack stroke depression diabetes cancer"):
        assert all(alt for alt in slot.split("|"))
