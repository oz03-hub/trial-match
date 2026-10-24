import pytest
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent import build_agent, build_messages, run_turn
from app.schemas import AgentTurn, ChatMessage, ChatRequest, TrialMatchResponse
from app.service import normalize

TURN_TOOL = ToolStrategy(AgentTurn).schema_specs[0].name

TURN_ARGS = {
    "assistant_message": "Found one diabetes trial.",
    "looks_like_a_fit": [],
    "worth_a_closer_look": [{
        "nct_id": "NCT00000001",
        "why": "Type 2 diabetes study.",
        "criteria": [{"text": "HbA1c 7-10.5%", "status": "unknown",
                      "quote": "HbA1c between 7.0% and 10.5%"}],
        "question": "Do you know your latest HbA1c?",
    }],
    "next_question": {"text": "What was your last HbA1c?", "suggested_answers": ["Under 7%", "7-10.5%", "Not sure"]},
    "done": False,
}


class FakeToolModel(GenericFakeChatModel):
    """Scripted chat model that accepts tools and records what it was sent."""

    bound_tools: list = []
    seen: list = []

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = [getattr(t, "name", None) for t in tools]
        return self

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(list(messages))
        return super()._generate(messages, *args, **kwargs)


def call(name, args, i):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{i}"}])


def fake(*script):
    return FakeToolModel(messages=iter(script), seen=[])


def request(text="I'm 54 with type 2 diabetes in Boston", **kw):
    return ChatRequest(messages=[ChatMessage(role="user", content=text)], **kw)


def test_agent_searches_reads_and_returns_turn(store):
    model = fake(
        call("search_trials", {"query": "type 2 diabetes"}, 1),
        call("get_eligibility", {"nct_id": "NCT00000001"}, 2),
        call(TURN_TOOL, TURN_ARGS, 3),
    )
    turn = run_turn(request(), agent=build_agent(model=model, store=store))

    assert isinstance(turn, AgentTurn)
    assert turn.worth_a_closer_look[0].nct_id == "NCT00000001"
    assert set(model.bound_tools) >= {"search_trials", "get_eligibility", TURN_TOOL}
    # tool results were fed back to the model
    tool_msgs = [m for m in model.seen[-1] if isinstance(m, ToolMessage)]
    assert "NCT00000001" in tool_msgs[0].content
    assert "HbA1c between 7.0% and 10.5%" in tool_msgs[1].content

    out = normalize(turn, store)
    assert out.worth_a_closer_look[0].criteria[0].quote_verified


def test_plain_text_reply_gets_nudged(store):
    model = fake(AIMessage(content="Here are some trials..."), call(TURN_TOOL, TURN_ARGS, 1))
    turn = run_turn(request(), agent=build_agent(model=model, store=store))
    assert turn.assistant_message == "Found one diabetes trial."
    assert isinstance(model.seen[-1][-1], HumanMessage)  # the nudge


def test_tool_limit_still_allows_final_turn(store):
    model = fake(
        *[call("search_trials", {"query": "diabetes"}, i) for i in range(6)],
        call(TURN_TOOL, TURN_ARGS, 99),
    )
    turn = run_turn(request(), agent=build_agent(model=model, store=store, search_limit=2))
    assert isinstance(turn, AgentTurn)


def test_bad_tool_input_does_not_crash(store):
    model = fake(call("get_eligibility", {"nct_id": "NCT404"}, 1), call(TURN_TOOL, TURN_ARGS, 2))
    run_turn(request(), agent=build_agent(model=model, store=store))
    assert "No trial" in [m for m in model.seen[-1] if isinstance(m, ToolMessage)][0].content


def test_messages_include_previous_and_finish(store):
    prev = normalize(AgentTurn.model_validate(TURN_ARGS), store)
    req = ChatRequest(
        messages=[ChatMessage(role="user", content="hi"), ChatMessage(role="assistant", content="hello")],
        previous=prev,
        finish=True,
    )
    msgs = build_messages(req)
    assert msgs[0] == {"role": "user", "content": "hi"}
    assert msgs[-1]["role"] == "user"
    note = msgs[-1]["content"]
    assert "NCT00000001" in note and "unknown" in note and "HbA1c between 7.0% and 10.5%" in note
    assert "What was your last HbA1c?" in note
    assert "done=true" in note


def test_empty_conversation_ends_with_user_message():
    msgs = build_messages(ChatRequest(messages=[]))
    assert msgs and msgs[-1]["role"] == "user"
    assert build_messages(request("hello")) == [{"role": "user", "content": "hello"}]


def test_previous_without_lists_adds_nothing():
    req = request("hi", previous=TrialMatchResponse(assistant_message="x"))
    assert build_messages(req) == [{"role": "user", "content": "hi"}]


def test_tool_exception_becomes_error_message(store, monkeypatch):
    def boom(query):
        raise ValueError("index broken")

    monkeypatch.setattr(store, "search", boom)
    model = fake(call("search_trials", {"query": "x"}, 1), call(TURN_TOOL, TURN_ARGS, 2))
    turn = run_turn(request(), agent=build_agent(model=model, store=store))
    assert isinstance(turn, AgentTurn)
    errors = [m.content for m in model.seen[-1] if isinstance(m, ToolMessage)]
    assert "search_trials failed" in errors[0]


def note_of(req):
    msgs = build_messages(req)
    assert msgs[-1]["role"] == "user"
    return msgs[-1]["content"]


def test_english_default_adds_no_language_note():
    assert build_messages(request("hello")) == [{"role": "user", "content": "hello"}]


def test_language_instruction_in_app_note():
    note = note_of(request("Tengo diabetes", language="es"))
    assert "[TrialMatch app note]" in note
    assert "Spanish" in note
    # what to translate, what to leave alone
    for field in ("assistant_message", "why", "next_question", "suggested_answers", "question"):
        assert field in note
    assert "EXACT" in note and "English" in note  # quotes verbatim; search queries in English
    assert "6th-grade" not in note


@pytest.mark.parametrize("code,name", [
    ("es", "Spanish"), ("pt", "Portuguese"), ("zh", "Chinese (Simplified)"),
    ("ht", "Haitian Creole"), ("vi", "Vietnamese"),
])
def test_language_names(code, name):
    assert name in note_of(request(language=code))


def test_plain_language_instruction():
    note = note_of(request("I have diabetes", plain_language=True))
    assert "6th-grade" in note and "short sentences" in note
    assert "Spanish" not in note  # still English


def test_language_and_plain_language_combine_with_previous_and_finish(store):
    prev = normalize(AgentTurn.model_validate(TURN_ARGS), store)
    note = note_of(request("hi", language="vi", plain_language=True, previous=prev, finish=True))
    assert "Vietnamese" in note and "6th-grade" in note and "NCT00000001" in note and "done=true" in note
    assert note.count("[TrialMatch app note]") == 1


def test_language_with_no_messages_still_greets():
    msgs = build_messages(ChatRequest(messages=[], language="pt"))
    assert "Portuguese" in msgs[-1]["content"]
    assert len(msgs) == 2 and "hasn't written" in msgs[0]["content"]
