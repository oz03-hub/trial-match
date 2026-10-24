from app.schemas import AgentCriterion, AgentTrial, AgentTurn
from app.service import GENERIC_QUESTION, normalize, quote_in


def crit(status="met", quote="Diagnosis of type 2 diabetes"):
    return AgentCriterion(text="criterion", status=status, quote=quote)


def trial(nct_id="NCT00000001", criteria=None, question=None):
    return AgentTrial(nct_id=nct_id, why="relevant", criteria=criteria or [crit()], question=question)


def turn(fit=(), closer=()):
    return AgentTurn(assistant_message="hi", looks_like_a_fit=list(fit), worth_a_closer_look=list(closer), next_question=None)


def ids(trials):
    return [t.nct_id for t in trials]


def test_unknown_ids_dropped(store):
    out = normalize(turn(fit=[trial("NCT99999999")], closer=[trial("bogus")]), store)
    assert out.looks_like_a_fit == [] and out.worth_a_closer_look == []


def test_enriched_from_csv(store):
    out = normalize(turn(fit=[trial(" nct00000001 ")]), store)
    t = out.looks_like_a_fit[0]
    assert t.nct_id == "NCT00000001"
    assert t.title == "Metformin Plus Exercise in Type 2 Diabetes"
    assert t.phase == "Phase 2"
    assert t.url == "https://clinicaltrials.gov/study/NCT00000001"
    assert len(t.sites) == 3
    assert t.why == "relevant"


def test_quote_verification(store):
    good = crit(quote="  * diagnosis of TYPE 2   diabetes ")
    bad = crit(quote="Must live on Mars")
    out = normalize(turn(closer=[trial(criteria=[good, bad], question="q?")]), store)
    c = out.worth_a_closer_look[0].criteria
    assert c[0].quote_verified is True
    assert c[0].quote == "diagnosis of TYPE 2   diabetes"
    assert c[1].quote_verified is False


def test_quote_in_handles_quotes_and_bullets():
    text = "Inclusion:\n* Adults aged 40 to 75 years\n"
    assert quote_in('"Adults aged 40 to 75 years"', text)
    assert quote_in("- adults aged 40\nto 75 years", text)
    assert not quote_in("", text)
    # punctuation and symbols don't matter
    assert quote_in("Adults, aged 40 to 75 years.", text)
    assert quote_in("ADULTS (aged 40-to-75 years)", text)
    escaped = "* Low activity (\\<150 minutes/week) \\[PHQ-9\\]"
    assert quote_in("Low activity (<150 minutes/week) [PHQ-9]", escaped)
    assert quote_in("Low activity (\\<150 minutes/week)", escaped)


def test_structured_fields_quotable(store):
    c = crit(quote="Ages: 40 Years-75 Years")
    out = normalize(turn(fit=[trial(criteria=[c])]), store)
    assert out.looks_like_a_fit[0].criteria[0].quote_verified


def test_fit_with_unknown_or_unmet_demoted(store):
    out = normalize(turn(fit=[
        trial("NCT00000001", criteria=[crit("met"), crit("unknown")]),
        trial("NCT00000002", criteria=[crit("met")]),
        trial("NCT00000003", criteria=[crit("unmet")], question="Are you healthy?"),
    ]), store)
    assert ids(out.looks_like_a_fit) == ["NCT00000002"]
    assert ids(out.worth_a_closer_look) == ["NCT00000001", "NCT00000003"]
    assert out.worth_a_closer_look[1].question == "Are you healthy?"


def test_fit_without_criteria_demoted(store):
    out_trial = normalize(
        AgentTurn(assistant_message="x", looks_like_a_fit=[AgentTrial(nct_id="NCT00000001", why="w", criteria=[])],
                  worth_a_closer_look=[], next_question=None),
        store,
    )
    assert out_trial.looks_like_a_fit == []
    assert ids(out_trial.worth_a_closer_look) == ["NCT00000001"]


def test_closer_look_gets_generic_question(store):
    out = normalize(turn(closer=[trial(criteria=[crit("unknown")]), trial("NCT00000002", question="  ")]), store)
    assert all(t.question == GENERIC_QUESTION for t in out.worth_a_closer_look)


def test_fit_items_have_no_question(store):
    out = normalize(turn(fit=[trial(question="leftover?")]), store)
    assert out.looks_like_a_fit[0].question is None


def test_dedupe_fit_wins(store):
    out = normalize(turn(
        fit=[trial("NCT00000001"), trial("NCT00000001")],
        closer=[trial("NCT00000001", question="q"), trial("NCT00000002", question="q"), trial("NCT00000002", question="q")],
    ), store)
    assert ids(out.looks_like_a_fit) == ["NCT00000001"]
    assert ids(out.worth_a_closer_look) == ["NCT00000002"]


def test_passthrough_fields(store):
    t = AgentTurn(assistant_message="hello", looks_like_a_fit=[], worth_a_closer_look=[], next_question=None, done=True)
    out = normalize(t, store)
    assert out.assistant_message == "hello" and out.done is True and out.error is False


def test_quote_in_tolerates_small_edits_but_not_invention():
    text = "Inclusion: Adults aged 40 to 75 years with a diagnosis of type 2 diabetes and HbA1c between 7% and 10%"
    assert quote_in("Adults aged 40 to 75 years ... diagnosis of type 2 diabetes", text)  # ellipsis join
    assert quote_in("Adults aged 40 to 75 years with a confirmed diagnosis of type 2 diabetes", text)  # one extra word
    assert not quote_in("Must live on Mars", text)
    assert not quote_in("Adults with the of and", text)  # common words alone
    assert not quote_in("Adults aged 40", "Adults aged 41 to 75")  # short quote must be exact
