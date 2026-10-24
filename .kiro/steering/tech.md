# Tech Stack

## Backend (`backend/app/`, Python via uv)

- FastAPI serving `/api/health`, `/api/chat`, and the built SPA.
- LangChain `create_agent` loop on OpenRouter via standard chat completions
  (default model `z-ai/glm-5.3-flash`). Two tools: `search_trials`, `get_eligibility`.
- Structured output uses `ToolStrategy(AgentTurn)`.
- Any agent/LLM failure returns HTTP 200 with `error: true`, a friendly message, and the
  previous lists — the UI must never see a 500.

### Commands

```bash
cd backend && uv sync
uv run uvicorn app.main:app --reload --port 8000   # dev server
uv run pytest -q                                   # tests (live test runs if OPENROUTER_API_KEY set)
uv run python -m app.agent "I'm 54 with type 2 diabetes in Boston"   # one CLI turn
```

## Frontend (`frontend/src/`)

- Vite + React + TypeScript + Tailwind (Tailwind v4, CSS-based config in `index.css`).
- No router, no state library. `App.tsx` holds all state.
- `react-markdown` renders the report and does not render raw HTML.

### Commands

```bash
cd frontend && npm install
npm run dev                 # dev server, proxies /api -> :8000
npm run build               # tsc -b && vite build; outputs frontend/dist
npm test -- --run           # Vitest + React Testing Library
```

## Full-app / deploy

- Build the frontend first; FastAPI then serves `frontend/dist` at `/` alongside `/api/*`.
- One multi-stage Docker image (Node builds frontend, Python/uv runtime serves). Binds to
  `$PORT`.

## Environment variables

`OPENROUTER_API_KEY` (required), `MODEL_NAME`, `OPENROUTER_BASE_URL`, `PORT`, `DATA_PATH`,
`HOSPITALS_PATH`.

## Conventions

- Always run the build and relevant tests after changes (frontend: `npm run build` +
  `npm test -- --run`; backend: `uv run pytest -q`).
- Match existing style and libraries; do not introduce new dependencies without reason.
- Keep translated UI strings in `frontend/src/i18n.ts`; eligibility quotes stay English.
