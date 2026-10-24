from app.report import DISCLAIMER, LABELS, build_report
from app.schemas import AgentCriterion, AgentTrial, AgentTurn, TrialMatchResponse
from app.service import normalize


def make_response(store):
    met = AgentCriterion(text="Has type 2 diabetes", status="met", quote="Diagnosis of type 2 diabetes")
    unknown = AgentCriterion(text="Women only", status="unknown", quote="Women with metastatic breast cancer")
    turn = AgentTurn(
        assistant_message="done",
        looks_like_a_fit=[AgentTrial(nct_id="NCT00000001", why="Studies type 2 diabetes.", criteria=[met])],
        worth_a_closer_look=[
            AgentTrial(nct_id="NCT00000002", why="Breast cancer imaging.", criteria=[unknown],
                       question="Is your cancer metastatic?"),
            AgentTrial(nct_id="NCT00000003", why="Healthy volunteers.", criteria=[unknown], question="q?"),
        ],
        next_question=None,
        done=True,
    )
    return normalize(turn, store)


def test_report_contents(store):
    md = build_report(make_response(store))
    # fit before closer look
    assert md.index("Metformin Plus Exercise") < md.index("Imaging Study in Breast Cancer")
    assert "https://clinicaltrials.gov/study/NCT00000001" in md
    assert "Phase 2" in md
    assert "Studies type 2 diabetes." in md
    assert "Has type 2 diabetes" in md and "Diagnosis of type 2 diabetes" in md
    assert "Is your cancer metastatic?" in md
    # recruiting sites with city + contact, central fallback
    assert "UMass Memorial" in md and "Worcester" in md
    assert "Jane Doe, 617-555-0100, jane@example.org" in md
    assert "Baystate" not in md
    assert DISCLAIMER in md
    assert "<" not in md  # no raw HTML


def test_report_no_sites_or_contacts(store):
    md = build_report(make_response(store))
    trial3 = md[md.index("Sleep and Memory"):]
    assert "No recruiting sites listed" in trial3
    trial2 = md[md.index("Imaging Study"):md.index("Sleep and Memory")]
    assert "Dana-Farber" in trial2 and "contact via the [study page]" in trial2


def test_report_empty(store):
    from app.schemas import TrialMatchResponse

    md = build_report(TrialMatchResponse(assistant_message="x", done=True))
    assert "didn't find" in md
    assert DISCLAIMER in md


def test_report_shows_cms_rating(store):
    md = build_report(make_response(store))
    mgh = [l for l in md.splitlines() if "Mass General Hospital" in l][0]
    assert mgh.startswith("- ")
    assert "CMS rating ★★★★★ (5/5)" in md
    assert "★★★★☆" not in md
    # no match -> no rating line for that site
    assert md.count("CMS rating") == 1


def test_rating_stars():
    from app.report import stars

    assert stars(4) == "★★★★☆"
    assert stars(1) == "★☆☆☆☆"


def test_hospital_without_rating_omits_line(store):
    from app.schemas import Hospital

    resp = make_response(store)
    resp.looks_like_a_fit[0].sites[0].hospital = Hospital(
        name="X", hospital_type="Childrens", emergency=True, overall_rating=None)
    assert "CMS rating" not in build_report(resp).split("Worth a closer look")[0]


def test_report_in_spanish(store):
    md = build_report(make_response(store), language="es")
    assert "# Su informe de TrialMatch" in md
    assert "Parece una buena opción (1)" in md
    assert "Vale la pena revisar (2)" in md
    assert "✅ Cumple: " in md
    assert "Calificación de CMS ★★★★★ (5/5)" in md
    assert "Looks like a fit" not in md and "Recruiting sites" not in md
    assert LABELS["es"]["disclaimer"] in md
    # facts and quotes are never translated
    assert "Diagnosis of type 2 diabetes" in md and "https://clinicaltrials.gov/study/NCT00000001" in md


def test_every_language_has_every_label():

    assert set(LABELS) == {"en", "es", "pt", "zh", "ht", "vi"}
    for lang, labels in LABELS.items():
        assert labels.keys() == LABELS["en"].keys(), lang
        assert all(v.strip() for v in labels.values()), lang


def test_all_languages_render(store):

    resp = make_response(store)
    reports = {lang: build_report(resp, language=lang) for lang in LABELS}
    assert len(set(reports.values())) == len(LABELS)
    assert reports["en"] == build_report(resp)
    empty = {lang: build_report(TrialMatchResponse(assistant_message="x", done=True), lang) for lang in LABELS}
    assert empty["zh"] != empty["en"]


def email_lines(md: str, title: str) -> list[str]:
    """The blockquote lines of the trial whose title is `title`."""
    start = md.index(f"### {title}")
    end = md.find("\n---", start)
    return [l for l in md[start:end if end != -1 else None].splitlines() if l.startswith(">")]


def test_report_has_separators_and_email_per_trial(store):
    md = build_report(make_response(store))
    # one email per trial, each a blockquote (no raw HTML)
    assert md.count("**Subject:**") == 3
    assert md.count("> [Your name]") == 3 and md.count("> [Phone or email]") == 3
    assert md.count("Matched with TrialMatch.org — pre-screened against the published eligibility criteria;"
                    " final eligibility is up to the study team.") == 3
    # rules between trials, between the two groups, and before the disclaimer
    assert md.count("\n---\n") == 1 + 1 + 1
    assert "## Worth a closer look (2)" in md


def test_email_greeting_and_subject(store):
    md = build_report(make_response(store))
    mgh = "\n".join(email_lines(md, "Metformin Plus Exercise in Type 2 Diabetes"))
    assert '> **Subject:** Interest in "Metformin Plus Exercise in Type 2 Diabetes" (NCT00000001)' in mgh
    assert "> Dear Study Team," in mgh
    sleep = "\n".join(email_lines(md, "Sleep and Memory"))
    assert "> Dear Study Team," in sleep


def test_email_uses_llm_body_and_cleans_greeting(store):
    body = "Dear Dr. X,\n\nI am 54 and have type 2 diabetes. Is HbA1c required?"
    md = build_report(make_response(store), emails={"NCT00000001": body})
    mgh = "\n".join(email_lines(md, "Metformin Plus Exercise in Type 2 Diabetes"))
    assert "> I am 54 and have type 2 diabetes. Is HbA1c required?" in mgh
    assert "Dr. X" not in mgh  # model's greeting dropped; code's greeting used
    assert "> Dear Study Team," in mgh
    # other trials still get the fallback
    assert "I am interested in the study" in md


def test_email_fallback_template(store):
    resp = make_response(store)
    resp.worth_a_closer_look[0].criteria[0].text = "Women only"
    md = build_report(resp)
    fit = "\n".join(email_lines(md, "Metformin Plus Exercise in Type 2 Diabetes"))
    assert '> I am interested in the study "Metformin Plus Exercise in Type 2 Diabetes" (NCT00000001).' in fit
    assert '> - Has type 2 diabetes (study criterion: "Diagnosis of type 2 diabetes")' in fit
    assert "next steps" in fit
    closer = "\n".join(email_lines(md, "Imaging Study in Breast Cancer"))
    assert "these study criteria look met" not in closer
    assert "> - Could you tell me what is needed to check: Women only?" in closer


def test_email_fallback_non_english_uses_english_quotes(store):
    resp = make_response(store)
    resp.looks_like_a_fit[0].criteria[0].text = "Tiene diabetes tipo 2"
    md = build_report(resp, language="es")
    fit = "\n".join(email_lines(md, "Metformin Plus Exercise in Type 2 Diabetes"))
    assert "> - Diagnosis of type 2 diabetes" in fit and "Tiene diabetes" not in fit
    assert LABELS["es"]["email"] in md


def test_email_body_list_and_paragraph_stay_separate(store):
    body = "Intro:\n- I am 54.\n- I live in Worcester.\nCould you confirm?"
    md = build_report(make_response(store), emails={"NCT00000001": body})
    q = "\n".join(email_lines(md, "Metformin Plus Exercise in Type 2 Diabetes"))
    assert "> Intro:\n>\n> - I am 54.\n> - I live in Worcester.\n>\n> Could you confirm?" in q
