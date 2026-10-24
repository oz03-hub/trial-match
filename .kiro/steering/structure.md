# Project Structure

```
backend/app/     FastAPI + LangChain agent (Python, uv)
frontend/src/    Vite + React + TypeScript + Tailwind SPA
data/            CSV data (gitignored large files)
```

## Backend (`backend/app/`)

| File | Role |
|---|---|
| `trials.py` | Loads `data/ma_clinical_trials_recruiting.csv`, dedupes by `nct_id`. Keeps only `RECRUITING` sites; site contact falls back to `central_contacts`. Blank age/sex means "unknown", never a filter. Provides keyword `search` (AND across words, `a\|b` for OR) and `get_eligibility`. |
| `synonyms.py` | Curated lay→medical synonym map; phrases matched first, short terms only on word boundaries. |
| `hospitals.py` | Matches a site (facility + city) to a CMS hospital rating (`data/data.csv`), favoring precision. Satellites inherit the parent rating. |
| `agent.py` | LangChain `create_agent` loop on OpenRouter. Tools: `search_trials`, `get_eligibility`. `ToolStrategy(AgentTurn)` structured output. Middleware for retries, tool-error-to-message, per-tool call limits, plain-text nudge. |
| `prompts.py` | System prompt + per-request language / plain-language instruction. Enforces "looks like a fit", no medical advice, exact quotes, one question per turn. |
| `schemas.py` | Wire contract. `AgentTurn` = what the LLM fills in (judgments only). `TrialMatchResponse` = what the API returns. |
| `service.py` | `normalize`: enriches agent judgments with CSV facts (title, phase, sites, contacts, URL), drops unknown ids, enforces list rules. |
| `report.py` | Builds the final markdown report deterministically from the final lists. |
| `main.py` | `/api/health`, `/api/chat`, serves the built SPA. Errors return HTTP 200 with `error: true`. |

## Frontend (`frontend/src/`)

- `App.tsx` — holds all state (no router, no state library).
- `api.ts` / `types.ts` — API client and shared types.
- `i18n.ts` — translated UI strings (6 languages). Eligibility quotes stay English.
- `components/Chat.tsx` — chat + suggested-answer buttons + searching indicator.
- `components/SidePanel.tsx` — the two lists.
- `components/TrialDrawer.tsx` — per-criterion checklist, sites, contacts.
- `SiteMap.tsx` + `mapPins.ts` — Leaflet/OSM map (green = fit, amber = closer look).
- `components/HospitalInfo.tsx` — CMS hospital rating display.
- `Report.tsx` — renders report with `react-markdown`.
- Tests: `App.test.tsx`, `map.test.tsx` (Vitest + RTL).

## Data flow

```
browser (React) --POST /api/chat {messages, previous, finish}--> FastAPI
   ^  holds all state                                            |
   +----- TrialMatchResponse (JSON) <- normalize <- agent <-tools-> in-memory CSV
```

Each request resends the full conversation plus the previous structured response. The
agent gets a compact summary of the previous lists so it updates them instead of
starting over.
