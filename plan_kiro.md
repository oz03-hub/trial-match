# Implementation Plan — TrialMatch (Hackachusetts 2026)

## Problem Statement
Build a single-page web prototype where a user describes themselves in plain language and a multi-round LangChain agent (over OpenRouter) matches them to recruiting Massachusetts clinical trials. The full conversation is visible; a side panel shows two continuously-updated lists ("looks like a fit" / "worth a closer look") plus a collapsed "ruled out" count; the agent asks one structured clarifying question at a time with suggested-answer buttons; and on "all done" it emits a markdown report of matched trials with recruiting-site locations and contacts. Monorepo, single FastAPI service serving a built React frontend. No accounts, no server-side storage.

## Requirements (confirmed with user)
- LLM backend: OpenRouter. Reuse the existing `lang_chain_agent.py` ReAct loop; strip research-experiment artifacts; make it robust on OpenRouter. Default OFF the Responses API path (the file's own comments warn gpt-oss tool calls get dropped on OpenRouter's Responses shim); use a tool-calling-friendly model via standard chat completions. If the user's working setup actually relies on the Responses-API path, keep it — confirm during Task 3.
- Retrieval: keep grep over the full CSV (`data/ma_clinical_trials_recruiting.csv`). Multi-round agent. ChromaDB documented only as a fallback, NOT built.
- Agent design: agent-driven end to end. The agent greps and reasons, emitting structured output each turn.
- Output model: hybrid. Structured JSON every turn drives the two side-panel lists + ruled-out count; a final markdown report is produced on "all done."
- Clarifying question: one structured question per turn with suggested-answer buttons rendered by the UI.
- Final report: only recruiting sites per trial; fall back to `central_contacts` when `site_contacts` is blank.
- Design principles: never say "you qualify" — use "looks like a fit" and defer to study coordinator for final decision. No medical advice — frame everything as "what to ask." Privacy: conversation state lives in the browser and is resent with each request; agent is stateless server-side.

## Background (findings from code + data)
- `lang_chain_agent.py` is a deep-research ReAct agent. Its `search` tool POSTs to a separate retriever HTTP service; it targets self-hosted vLLM and returns free text (`Explanation / Exact Answer / Confidence`). Needed changes: (a) new grep tool over the local CSV replacing the HTTP retriever, (b) structured JSON output instead of free text, (c) OpenRouter-friendly model client. Trim research artifacts (rollout recorder, vLLM-specific comments, confidence-format prompt). Keep useful middleware (tool retry/limit, final-answer nudge).
- Data shape: `data/ma_clinical_trials_recruiting.csv` is ONE ROW PER (trial × site), ~147k rows. Columns: `nct_id, brief_title, overall_status, conditions, phases, min_age, max_age, sex, healthy_volunteers, central_contacts, facility, city, state, zip, site_status, lat, lon, site_contacts, brief_summary, eligibility_criteria, url`. Many rows have `site_status = NOT_YET_RECRUITING`; `min_age/max_age`, `central_contacts`, `site_contacts` are often blank. Report needs trial-level dedup + "recruiting sites only, fall back to central contact." Blank age/sex = "unknown," not a hard filter.
- `data/data.csv` = CMS MA hospital ratings (84 rows: `facility_id, facility_name, city, county, hospital_type, ownership, emergency, overall_rating`). Supports the "nearby hospitals" stretch goal. No PLACES county-health file present — PLACES/equity stretch goals out of scope unless a file is added.
- No existing scaffolding: no requirements.txt, frontend, .env, or git repo.

## Per-turn contract (Pydantic; UI renders from this, never raw text for lists)
```
TrialMatchResponse {
  assistant_message: str
  looks_like_a_fit: Trial[]        # all checkable criteria met, nothing important unknown
  worth_a_closer_look: Trial[]     # promising; each carries the unmet/unknown resolving question
  ruled_out_count: int
  ruled_out: RuledOut[]            # {nct_id, title, reasons[]}
  next_question: { text: str, suggested_answers: str[] } | null
  done: bool
  final_report_markdown: str | null   # populated only when done
}
Trial { nct_id, title, phase, criteria: {text, status: met|unmet|unknown, quote}[], sites, url }
```
State lives in the browser (messages + collected answers), resent with each `/api/chat` call; server-side agent is stateless.

## Task Breakdown (test-driven, incremental; each ends wired together)

### Task 1: Project scaffold + health check.
- Objective: Create monorepo layout (`backend/`, `frontend/`, keep `data/`), `requirements.txt` (fastapi, uvicorn, langchain, langchain-openai, python-dotenv, pydantic, pytest, httpx), `.env.example` (`OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `MODEL_NAME`, `PORT`), `.gitignore`. FastAPI app with `GET /api/health`.
- Tests: pytest hits `/api/health` → 200 `{"status":"ok"}`.
- Demo: uvicorn serves the health endpoint.

### Task 2: Trial data access layer (deterministic, tested).
- Objective: `trials.py` reading the CSV: trial-level dedup (group rows by `nct_id`), per-trial recruiting-site extraction (`site_status == RECRUITING`, contact fallback `site_contacts → central_contacts`), and `grep(query)` returning matching trial blocks for the agent tool. Explicit blank-field policy (missing age/sex = "unknown," not a hard filter).
- Tests: unit tests on a small fixture CSV covering dedup, recruiting-only filtering, contact fallback, blank handling.
- Demo: script/test prints matched trial blocks and a deduped trial with recruiting sites + contacts.

### Task 3: Adapt the LangChain agent for OpenRouter + local grep tool.
- Objective: Refactor `lang_chain_agent.py` into `backend/agent.py`: replace HTTP `search` tool with the local grep tool from Task 2; switch model client to OpenRouter via standard chat completions (default off the Responses-API path; confirm with user if their setup needs it); strip research artifacts; keep tool retry/limit + final-answer-nudge middleware. Write the TrialMatch system prompt encoding design principles ("looks like a fit," no medical advice, defer to coordinator).
- Tests: mocked-LLM test asserts the agent invokes the grep tool and loops; one live smoke test (skipped without API key) returns non-empty answer.
- Demo: CLI run — type a description, watch multi-round grep, produce a text answer.

### Task 4: Structured JSON output (per-turn contract).
- Objective: Define Pydantic models (TrialMatchResponse, Trial, criterion status, next_question, done, final_report_markdown); agent emits them via structured output / output parser. Enforce per-criterion status ∈ {met, unmet, unknown} with a quoted eligibility line; "worth a closer look" items each carry the resolving question; next_question = single most useful clarifying question. THIS IS THE RISKIEST PART — front-load validation here.
- Tests: parse/validate sample agent output; assert invariants (fit items have no unmet criteria; closer-look items have ≥1 unknown/unmet with a question; ruled_out_count matches list length).
- Demo: CLI prints well-formed JSON with populated lists + clarifying question.

### Task 5: `/api/chat` endpoint (stateless, browser-held history).
- Objective: `POST /api/chat` accepting `{messages[], answers{}}`, invoking the agent, returning TrialMatchResponse JSON. No server-side storage. Graceful error handling (LLM/network failures → friendly message, never a 500 to the UI).
- Tests: endpoint test with mocked agent asserts request→response shape and error handling.
- Demo: curl a description to `/api/chat`, get structured JSON.

### Task 6: Frontend scaffold + chat panel wired to the API.
- Objective: Vite + React + Tailwind app with a left chat panel. Send conversation history to `/api/chat`; render full visible conversation; render `next_question` as text with suggested-answer buttons; clicking a button or typing submits the next turn. Conversation state in browser memory.
- Tests: component test for message rendering and suggested-answer button submission (Vitest/RTL).
- Demo: in-browser chat round-trips with real backend; clarifying questions appear with clickable answers.

### Task 7: Side panel with the two live lists + ruled-out section.
- Objective: Right-hand panel rendering `looks_like_a_fit` and `worth_a_closer_look`, updating every turn; collapsed "ruled out" section showing count, expandable to reasons. "Worth a closer look" items display the exact resolving question.
- Tests: component tests — lists re-render on updated responses; ruled-out expand/collapse works.
- Demo: answering a clarifying question visibly moves trials between lists.

### Task 8: Trial detail drawer.
- Objective: Clicking a trial opens a drawer: plain-language summary, phase explanation, per-criterion checklist (met/unmet/unknown with quoted eligibility line), recruiting site(s) + city, contact info (site→central fallback), and `clinicaltrials.gov/study/{NCTId}` link.
- Tests: component test rendering criterion statuses and the study link from sample data.
- Demo: open any trial, inspect full criteria/contacts/link.

### Task 9: Final markdown report on "all done."
- Objective: When agent returns `done: true`, backend populates `final_report_markdown` (matched trials, recruiting-site locations, contacts, links); frontend renders it as a distinct report view/section with sanitized markdown. Agent says "all done" in chat.
- Tests: assert `done` triggers non-empty report containing expected trials/contacts; frontend renders markdown safely.
- Demo: full conversation ends with agent declaring done and showing a formatted report.

### Task 10: Single-service packaging + deploy config.
- Objective: Build frontend to static files; FastAPI serves them (SPA fallback), binds to `$PORT`, API key from env, `data/` included. Add Render/Railway config + README with Cloudflare Tunnel fallback instructions.
- Tests: confirm static index served at `/` and `/api/*` still routes; build smoke check.
- Demo: one command runs the whole app on `$PORT`, deployable to Render/Railway.

### Task 11: Map of recruiting sites.
- Objective: Side panel gets a Lists | Map toggle. Leaflet + OpenStreetMap pins for every recruiting site (CSV `lat`/`lon`, exposed as `Site.lat/lon`), colored by list (fit = green, closer look = amber), with sites at the same coordinates grouped into one pin. Each popup opens the trial drawer.
- Tests: pure `sitesToPins` helper (grouping, colors); mocked react-leaflet render.

### Task 12: CMS hospital context.
- Objective: `backend/app/hospitals.py` matches trial sites to `data/data.csv` (CMS MA hospital ratings) by normalized name + city, favoring precision over recall. `Site.hospital = {name, hospital_type, emergency, overall_rating}`. The drawer and the report show star ratings and an emergency badge.
- Tests: fixture hospitals CSV; known-name matches; no false matches across cities.

### Task 13: Language + plain-language mode.
- Objective: `ChatRequest.language` (en/es/pt/zh/ht/vi) and `plain_language` (~6th-grade level). Each is passed to the agent as an instruction, and quotes stay exact English for verification. The report's fixed labels and disclaimer are translated. The UI has a language select, a plain-language toggle, and key strings translated.
- Tests: instruction injected; report labels switch; request body carries both fields.

### Task 14: Condition synonym expansion before grep.
- Objective: `backend/app/synonyms.py` is a curated lay→medical map (e.g. heart attack → myocardial infarction|MI). `search` expands it before grepping: multi-word phrases first, OR within a slot, AND across slots, and short synonyms matched on word boundaries.
- Tests: lay term finds medical-term trial; AND preserved; "MI" ≠ "migraine".

### Task 15: Example persona buttons.
- Objective: one-click persona chips on the start screen send a realistic first message, for a fast demo.
- Tests: click sends message; chips hidden after start.

## Scope changes
- "Ruled out" list + count removed (too much overhead). Only "looks like a fit" + "worth a closer look".
- Data is 4,478 rows / 3,145 trials (not ~147k).
- Model: OpenRouter `z-ai/glm-5.3-flash` via chat completions (no Responses API).

## Deferred / out of scope (stretch; optional follow-ups)
SSE streaming of agent reasoning; zip/distance filtering; PLACES equity view (no PLACES file present — needs data source); evaluation persona set; ChromaDB retrieval fallback.
