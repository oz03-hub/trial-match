import pytest
from fastapi.testclient import TestClient

from app import main
from app.schemas import AgentCriterion, AgentTrial, AgentTurn, NextQuestion
from app.service import normalize


@pytest.fixture
def client(monkeypatch, store):
    monkeypatch.setattr(main, "get_store", lambda: store)
    monkeypatch.setattr(main, "generate_emails", lambda messages, response: {})  # no network
    return TestClient(main.app)


def agent_turn(done=False):
    crit = AgentCriterion(text="Type 2 diabetes", status="met", quote="Diagnosis of type 2 diabetes")
    return AgentTurn(
        assistant_message="Here is what I found.",
        looks_like_a_fit=[AgentTrial(nct_id="NCT00000001", why="T2D study", criteria=[crit])],
        worth_a_closer_look=[],
        next_question=None if done else NextQuestion(text="Age?", suggested_answers=["<40", "40-75"]),
        done=done,
    )


BODY = {"messages": [{"role": "user", "content": "I have type 2 diabetes"}]}


def test_chat_shape(client, monkeypatch):
    monkeypatch.setattr(main, "run_turn", lambda req: agent_turn())
    r = client.post("/api/chat", json=BODY)
    assert r.status_code == 200
    data = r.json()
    assert data["assistant_message"] == "Here is what I found."
    assert data["looks_like_a_fit"][0]["title"].startswith("Metformin")
    assert data["looks_like_a_fit"][0]["criteria"][0]["quote_verified"] is True
    assert data["next_question"]["suggested_answers"] == ["<40", "40-75"]
    assert data["done"] is False and data["final_report_markdown"] is None and data["error"] is False


def test_finish_builds_report(client, monkeypatch):
    seen = {}

    def fake_run(req):
        seen["finish"] = req.finish
        return agent_turn()  # agent forgot done=true; finish forces it

    monkeypatch.setattr(main, "run_turn", fake_run)
    r = client.post("/api/chat", json={**BODY, "finish": True})
    data = r.json()
    assert seen["finish"] is True
    assert data["done"] is True and data["next_question"] is None
    assert "NCT00000001" in data["final_report_markdown"]


def test_agent_done_builds_report(client, monkeypatch):
    monkeypatch.setattr(main, "run_turn", lambda req: agent_turn(done=True))
    data = client.post("/api/chat", json=BODY).json()
    assert data["done"] is True and "Metformin" in data["final_report_markdown"]


def test_error_carries_previous_lists(client, monkeypatch, store):
    def boom(req):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(main, "run_turn", boom)
    previous = normalize(agent_turn(), store).model_dump()
    r = client.post("/api/chat", json={**BODY, "previous": previous})
    assert r.status_code == 200
    data = r.json()
    assert data["error"] is True
    assert data["assistant_message"]
    assert [t["nct_id"] for t in data["looks_like_a_fit"]] == ["NCT00000001"]
    assert data["next_question"] == previous["next_question"]


def test_error_without_previous(client, monkeypatch):
    monkeypatch.setattr(main, "run_turn", lambda req: 1 / 0)
    data = client.post("/api/chat", json=BODY).json()
    assert data["error"] is True and data["looks_like_a_fit"] == []


def test_bad_request_is_422(client):
    assert client.post("/api/chat", json={"messages": [{"role": "robot", "content": "x"}]}).status_code == 422


def test_finish_report_uses_request_language(client, monkeypatch):
    monkeypatch.setattr(main, "run_turn", lambda req: agent_turn())
    data = client.post("/api/chat", json={**BODY, "finish": True, "language": "es"}).json()
    assert "Su informe de TrialMatch" in data["final_report_markdown"]
    assert client.post("/api/chat", json={**BODY, "language": "xx"}).status_code == 422


def test_error_message_uses_request_language(client, monkeypatch):
    monkeypatch.setattr(main, "run_turn", lambda req: 1 / 0)
    data = client.post("/api/chat", json={**BODY, "language": "es"}).json()
    assert data["assistant_message"] == main.ERROR_MESSAGES["es"]
