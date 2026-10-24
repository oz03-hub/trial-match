from langchain_core.messages import AIMessage

from app import main
from app.outreach import build_outreach_input, generate_emails
from app.schemas import ChatMessage, OutreachEmails
from app.report import build_report
from tests.test_agent import FakeToolModel, call, fake
from tests.test_report import make_response

MESSAGES = [
    ChatMessage(role="user", content="I'm 54 with type 2 diabetes"),
    ChatMessage(role="assistant", content="Where do you live?"),
    ChatMessage(role="user", content="Worcester"),
]
TOOL = "OutreachEmails"


def test_input_has_only_user_messages_and_judgments(store):
    text = build_outreach_input(MESSAGES, make_response(store).looks_like_a_fit)
    assert "I'm 54 with type 2 diabetes" in text and "Worcester" in text
    assert "Where do you live?" not in text
    assert "Trial NCT00000001: Metformin Plus Exercise" in text
    assert '[met] Has type 2 diabetes | quote: "Diagnosis of type 2 diabetes"' in text


def test_generate_emails_drops_unknown_ids_and_duplicates(store):
    model = fake(call(TOOL, {"emails": [
        {"nct_id": "NCT00000001", "body": "Hello from patient."},
        {"nct_id": "NCT99999999", "body": "invented trial"},
        {"nct_id": "NCT00000001", "body": "second one ignored"},
        {"nct_id": "NCT00000002", "body": "   "},
    ]}, 1))
    out = generate_emails(MESSAGES, make_response(store), model=model)
    assert out == {"NCT00000001": "Hello from patient."}
    sent = model.seen[0]
    assert "NCT00000001" in sent[-1].content and sent[0].type == "system"


def test_generate_emails_never_raises(store):
    class Boom(FakeToolModel):
        def _generate(self, *a, **k):
            raise RuntimeError("LLM down")

    assert generate_emails(MESSAGES, make_response(store), model=Boom(messages=iter([]), seen=[])) == {}
    # plain-text reply (no tool call) -> parse failure -> {}
    assert generate_emails(MESSAGES, make_response(store), model=fake(AIMessage(content="hi"))) == {}


def test_generate_emails_skips_llm_when_no_trials():
    from app.schemas import TrialMatchResponse

    class NoCall:
        def with_structured_output(self, *a, **k):
            raise AssertionError("should not be called")

    assert generate_emails(MESSAGES, TrialMatchResponse(assistant_message="x"), model=NoCall()) == {}


def test_report_survives_missing_trial_in_llm_output(store):
    resp = make_response(store)
    md = build_report(resp, emails={"NCT00000001": "Custom body."})
    assert md.count("**Subject:**") == 3
    assert "> Custom body." in md and "I am interested in the study" in md


def test_finish_passes_emails_into_report(monkeypatch, store):
    from fastapi.testclient import TestClient
    from tests.test_api import agent_turn

    monkeypatch.setattr(main, "get_store", lambda: store)
    monkeypatch.setattr(main, "run_turn", lambda req: agent_turn())
    seen = {}

    def fake_emails(messages, response):
        seen["msgs"] = [m.content for m in messages]
        return {"NCT00000001": "Patient-voice body here."}

    monkeypatch.setattr(main, "generate_emails", fake_emails)
    body = {"messages": [{"role": "user", "content": "I have type 2 diabetes"}], "finish": True}
    md = TestClient(main.app).post("/api/chat", json=body).json()["final_report_markdown"]
    assert seen["msgs"] == ["I have type 2 diabetes"]
    assert "> Patient-voice body here." in md
