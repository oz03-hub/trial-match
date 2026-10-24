# TrialMatch

Describe yourself in plain language; an LLM agent searches recruiting Massachusetts clinical trials over several rounds and sorts them into **Looks like a fit** and **Worth a closer look**. It asks one clarifying question per turn (with answer buttons), and when you click **All done**, it writes a markdown report listing recruiting sites and contacts.

## Problem

**For patients, finding a trial is a filtering problem they aren't equipped to solve.** Registries like ClinicalTrials.gov expect you to pick conditions, phases, statuses and locations from filter menus, then read dense eligibility criteria written for clinicians. Patients don't know which filters matter or what "HbA1c ≥ 7.5%" means for them, and eligibility criteria take about a college reading level to understand [[1]](https://pmc.ncbi.nlm.nih.gov/articles/PMC4765646/). Many give up before they find a trial they could have joined, and lose access to new treatments, free care and study compensation along with it.

**Patients are willing; access is the bottleneck.** About 7% of US adults with cancer enroll in a treatment trial [[2]](https://www.healthday.com/healthpro-news/cancer/patient-enrollment-in-cancer-treatment-trials-about-7-percent), yet 55% agree to join when they are offered one [[3]](https://pmc.ncbi.nlm.nih.gov/articles/PMC7936047/). For 56% of patients the barrier is that no trial was available at the center where they were treated [[4]](https://www.newswise.com/articles/new-research-shows-structural-barriers-are-the-biggest-reason-for-low-participation-in-clinical-trials), even when one may be recruiting elsewhere in the state.

**For researchers, the result is a small candidate pool.** Poor accrual caused 41% of the cardiovascular trials on ClinicalTrials.gov that failed to complete [[5]](https://bmjopen.bmj.com/content/7/6/e013482). The people who would qualify exist, but they never reach the study team.

**Our approach: search by conversation.** Talking to someone is the most natural way to search. You describe yourself in plain language, and a search agent does the filtering:

- It searches public clinical trial records with cheap, effective retrieval (keyword search plus lay→medical synonym expansion, run several times per turn).
- It narrows the candidates to a shortlist it carries from turn to turn, split into "looks like a fit" and "worth a closer look".
- It asks one follow-up question at a time, picked to settle the open criteria. Each answer narrows the list further or brings in trials that were borderline before.

Patients get to trials, treatments and study compensation without having to learn the registry. Researchers get a larger pool of candidates who were pre-screened against each eligibility criterion, with quoted evidence, before they ever contact the site. The study coordinator still makes the final call.

## Features

- **Two live lists:** "Looks like a fit" and "Worth a closer look", updated every turn. Each closer-look trial shows the question that would settle it.
- **One clarifying question per turn,** with suggested-answer buttons.
- **Trial drawer:** a per-criterion checklist (met/unmet/unknown with the quoted eligibility line, marked verified or not), recruiting sites, contacts, and the ClinicalTrials.gov link.
- **Site map:** a Lists | Map toggle. Leaflet + OpenStreetMap pins are blue for fit and gray for closer look; clicking one opens the trial.
- **Hospital context:** trial sites are matched to CMS Massachusetts hospital ratings (`data/data.csv`). Matched sites show stars, hospital type and an emergency-services badge.
- **Language + plain-language mode:** English, Spanish, Portuguese, Chinese, Haitian Creole and Vietnamese, plus an option for about a 6th-grade reading level. Quotes stay in the original English so they can be checked.
- **Lay-term synonyms:** "heart attack" is expanded to myocardial infarction|MI|… before searching.
- **Example persona buttons** for a one-click demo.
- **"All done" report:** markdown listing recruiting sites, contacts, CMS ratings and a disclaimer, in the chosen language. Each trial ends with a ready-to-send draft email to its contact (English, quote box, `[Your name]` placeholders). Copy, Download .md or Print/PDF.

Not medical advice. The study coordinator always makes the final eligibility decision.

## Quick start

```bash
cp .env.example .env            # set OPENROUTER_API_KEY

# backend (Python via uv)
cd backend && uv sync && uv run uvicorn app.main:app --reload --port 8000

# frontend dev server (separate terminal; proxies /api → :8000)
cd frontend && npm install && npm run dev
```

To run the whole app as a single service on one port, build the frontend first (`cd frontend && npm run build`). FastAPI then serves `frontend/dist` at `/` alongside `/api/*`.

CLI (one agent turn, prints JSON): `cd backend && uv run python -m app.agent "I'm 54 with type 2 diabetes in Boston"`

## Tests

```bash
cd backend && uv run pytest -q      # unit, fake-model agent, API; live test runs if OPENROUTER_API_KEY set
cd frontend && npm test -- --run    # Vitest + React Testing Library
```

## Design

```
browser (React)  ──POST /api/chat {messages, previous, finish}──▶  FastAPI
   ▲  holds all state                                              │
   └──────────── TrialMatchResponse (JSON) ◀── normalize ◀── LangChain agent ──tools──▶ in-memory CSV
```

**Stateless server, state in the browser.** Each request resends the full conversation plus the previous structured response. Nothing is stored server-side, so there are no accounts, no database, and nothing to clean up. The agent receives a compact summary of the previous lists so it updates them instead of starting over.

**Backend** (`backend/app/`)

| File | Role |
|---|---|
| `trials.py` | Loads `data/ma_clinical_trials_recruiting.csv` (one row per trial × site; 3,145 trials) and dedupes it by `nct_id`. Only `RECRUITING` sites are kept, and each site's contact falls back to `central_contacts` when it has none. Blank age/sex means "unknown", never a filter. Also provides keyword `search` (AND across words, `a\|b` for OR) and `get_eligibility`. |
| `synonyms.py` | A curated lay→medical synonym map that expands each query slot (phrases matched first; short terms only on word boundaries). |
| `hospitals.py` | Matches a site (facility + city) to a CMS hospital rating, favoring precision: same city, then an exact or contained normalized name, and ties give no match. About 52% of recruiting site rows match. Satellite sites inherit the parent hospital's rating. |
| `agent.py` | LangChain `create_agent` loop on OpenRouter using standard chat completions (default `z-ai/glm-5.3-flash`). It has two tools, `search_trials` and `get_eligibility`. Structured output uses `ToolStrategy(AgentTurn)`. Middleware: model and tool retry, tool error to message, per-tool call limits, and a nudge when the model answers in plain text. |
| `prompts.py` | System prompt, plus a per-request language / plain-language instruction. It enforces "looks like a fit" (never "qualify"), no medical advice, exact quotes from the eligibility text, and one question per turn. |
| `schemas.py` | The wire contract. `AgentTurn` is what the LLM fills in (judgments only); `TrialMatchResponse` is what the API returns. |
| `service.py` | `normalize`: enriches the agent's judgments with facts from the CSV (title, phase, sites, contacts, URL) and drops unknown ids. It also enforces the list rules (see below). |
| `report.py` | Builds the final markdown report deterministically from the final lists, with `---` between trials. Adds a per-trial outreach email as a `>` blockquote: code writes greeting ("Dear Study Team"), subject, sign-off and footer; the body comes from `outreach.py`, or a template built from met/unknown criteria if the LLM body is missing. |
| `outreach.py` | One fresh LLM call at report time (not the agent conversation): the patient's messages plus each trial's judged criteria in, `{nct_id, body}` out (patient voice, English, only stated facts). Unknown ids are dropped. Never raises; failure means the fallback template. |
| `main.py` | `/api/health`, `/api/chat`, and serving the built SPA. Any agent or LLM failure returns HTTP 200 with `error: true`, a friendly message, and the previous lists, so the UI never sees a 500. |

The `normalize` rules:
- A fit item with any `unmet` or `unknown` criterion moves to closer-look.
- Every closer-look item carries a resolving question.
- Each quote is checked against the trial's real eligibility text and gets `quote_verified`.

**The LLM decides; the data layer supplies the facts.** The model only outputs trial ids, per-criterion judgments (met/unmet/unknown plus a quote), and questions. Contacts, sites and links always come from the CSV, so they can't be hallucinated. The report is generated in code rather than by the LLM for the same reason.

**Frontend** (`frontend/src/`): Vite + React + TypeScript + Tailwind, with no router or state library.
- `App.tsx` holds the state.
- `components/Chat.tsx` is the chat and suggested-answer buttons; `SidePanel.tsx` is the two lists; `TrialDrawer.tsx` shows criteria, sites and contacts.
- `SiteMap.tsx` + `mapPins.ts` draw the map (pins grouped by coordinates); `HospitalInfo.tsx` shows the CMS rating; `i18n.ts` holds the translated UI strings.
- `Report.tsx` renders the report with `react-markdown`, which does not render raw HTML.

**Retrieval.** Keyword grep over about 19 MB held in memory is fast enough here, and the agent compensates for its limits by searching several times with synonyms. If recall turns out to be a problem, the documented fallback is an embedding index such as ChromaDB behind the same `search_trials` tool. It isn't built.

**Dropped from scope:** the "ruled out" list, streaming, zip/distance filtering, and a PLACES equity view.

**Translations** were written by the model and have not been reviewed by a native speaker.

## Deploy

One Docker image (multi-stage: Node builds the frontend, then a Python/uv runtime serves the API and static files). It binds to `$PORT`.

```bash
docker build -t trialmatch .
docker run -p 8000:8000 --env-file .env trialmatch
```

- **Render:** `render.yaml` is a Blueprint (Docker runtime, health check `/api/health`). Set `OPENROUTER_API_KEY` in the dashboard.
- **Railway / Fly:** point them at the Dockerfile and set `OPENROUTER_API_KEY`. `PORT` is injected.
- **Fallback (no cloud):** run locally, then `cloudflared tunnel --url http://localhost:8000` gives a public `trycloudflare.com` URL.

Environment variables: `OPENROUTER_API_KEY` (required), `MODEL_NAME`, `OPENROUTER_BASE_URL`, `PORT`, `DATA_PATH`, `HOSPITALS_PATH`.
