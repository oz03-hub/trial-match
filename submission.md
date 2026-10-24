# TrialMatch — Hackachusetts 2026 Submission

## Basics

- **Project:** TrialMatch
- **Track:** Healthcare & Biotech
- **Team (max 4):** TODO — Ozel Yilmazel (oyilmazel@cs.umass.edu), …
- **Repo (public):** https://github.com/oz03-hub/trial-match
- **Demo video (<3 min, YouTube/Vimeo, public):** TODO — URL
- **Live demo:** TODO — Render URL (or Cloudflare tunnel)

## Tagline

Finding and joining a clinical trial shouldn't be as difficult as it is. Describe yourself in plain language, and a conversational AI agent finds recruiting Massachusetts trials that look like a fit.

## Problem

- **Patients can't use registries.** ClinicalTrials.gov makes you pick conditions, phases and locations from filter menus, then read eligibility criteria that take about a college reading level to understand ([PMC4765646](https://pmc.ncbi.nlm.nih.gov/articles/PMC4765646/)).
- **Patients are willing, but they can't find trials.** About 7% of US adults with cancer enroll in a treatment trial ([HealthDay](https://www.healthday.com/healthpro-news/cancer/patient-enrollment-in-cancer-treatment-trials-about-7-percent)), yet 55% agree to join when they're offered one ([PMC7936047](https://pmc.ncbi.nlm.nih.gov/articles/PMC7936047/)). For 56% of patients, the barrier is that no trial was available at the center where they were treated ([Newswise](https://www.newswise.com/articles/new-research-shows-structural-barriers-are-the-biggest-reason-for-low-participation-in-clinical-trials)), even when one may be recruiting elsewhere in the state.
- **Researchers end up short on candidates.** Poor accrual caused 41% of the cardiovascular trials on ClinicalTrials.gov that failed to complete ([BMJ Open](https://bmjopen.bmj.com/content/7/6/e013482)).

## What it does

You describe yourself in a chat. A LangChain agent searches 3,145 recruiting Massachusetts trials over several rounds and keeps two live lists:

- **Looks like a fit:** every criterion it could check is met.
- **Worth a closer look:** promising, but with open questions. Each trial shows the question that would settle it.

Each turn, the agent asks **one clarifying question** with answer buttons, and each answer moves trials between the lists. Clicking **All done** produces a report of recruiting sites and contacts, with a draft email for each study team.

### Features

- **Per-criterion checklist** (met / unmet / unknown). Each item quotes the trial's eligibility text, and code checks the quote against the source and marks it *verified*.
- **Site map** (Leaflet + OpenStreetMap). Pins are colored by list, and clicking one opens the trial.
- **Hospital context.** Trial sites are matched to CMS Massachusetts hospital ratings, which show stars, hospital type and an emergency-services badge.
- **6 languages** (EN, ES, PT, ZH, Haitian Creole, VI) plus a **plain-language mode** at about a 6th-grade reading level. Quotes stay in English so they can be checked.
- **Lay → medical synonym expansion** (for example, "heart attack" → myocardial infarction | MI).
- **Final report.** It lists sites, contacts and ratings, plus a ready-to-send outreach email per trial written in the patient's voice. Copy, download as .md, or print to PDF.
- **Example persona buttons** for a one-click demo.

### Design choices

- **The LLM decides; the data supplies the facts.** The model outputs only trial IDs, judgments, quotes and questions. Titles, sites, contacts and links come from the CSV, so they can't be hallucinated. Code generates the report.
- **Safety wording.** The app says "looks like a fit", never "you qualify", gives no medical advice, and leaves the final eligibility decision to the study coordinator.
- **Privacy.** The server is stateless: no accounts, no database, and the conversation lives only in the browser.
- **Robust.** Any LLM failure returns a friendly message and keeps the previous lists, so the UI never shows a 500.

### Evaluation: 95% recall in one turn

We ran 20 test prompts ([`kiro_prompts.tsv`](kiro_prompts.tsv)), each written to match one specific recruiting trial. They span rare cancers, pediatric epilepsy, dermatology, IVF, healthy-volunteer vaccine studies and more. The agent got a single message from each patient and no follow-up answers.

- **Result: in 19 of 20 cases (95%), the target trial appeared in the agent's lists** from among 3,145 trials.
- **Caveat:** these prompts describe each trial's eligibility in detail, so they are an easy benchmark. Real patients give less detail, which is why the agent asks follow-up questions.

### Who benefits and how it scales

- **Patients**, especially people who aren't treated at an academic center, people with limited English, and people with low health literacy, get access to trials, new treatments and study compensation.
- **Research teams** get candidates who were pre-screened against each criterion, with quoted evidence.
- **Scaling.** The data layer is a ClinicalTrials.gov API v2 snapshot filtered to MA, and it can be swapped to any state or the whole country. The retrieval tool has a documented upgrade path to embeddings (ChromaDB) behind the same interface. It deploys as one Docker image.

### Data sources

- ClinicalTrials.gov API v2 (MA, recruiting sites)
- CMS Hospital General Information (MA ratings)
- OpenStreetMap tiles

### Stack

FastAPI · LangChain `create_agent` · OpenRouter (`z-ai/glm-5.3-flash`) · Pydantic structured output · React + TypeScript + Vite + Tailwind · Leaflet · Docker / Render.

## How we used Kiro

### Tools: Kiro CLI

We used the Kiro CLI (v2.33) for the whole project, mostly with the `auto` model and switching to Claude Sonnet 5.5 for some tasks.

### Spec-driven development: plan first, then build

1. **Brief to plan.** We pasted a one-page product brief (goal, user flow, design principles, data, architecture, stretch goals, non-goals) into Kiro's planning mode.
2. **Kiro asked clarifying questions first,** as multiple-choice options:
   - which LLM backend to use (OpenRouter, reusing our existing research agent);
   - what the output should look like (structured JSON every turn, plus a markdown report at the end);
   - how to ask questions (one per turn, with answer buttons);
   - how the layout should work (full conversation visible, lists in a side panel).
3. **It inspected our data before planning.** It found that the CSV has one row per trial × site and that age and contact fields are often blank, and wrote rules for both into the plan: dedupe by trial, keep recruiting sites only, fall back to the central contact, and treat a blank field as "unknown", not as a filter.
4. **It wrote the spec to [`plan_kiro.md`](plan_kiro.md):**
   - the problem statement and confirmed requirements;
   - a Pydantic **per-turn contract**;
   - **15 test-driven tasks**, each with an objective, tests and a demo, that each ended in a working app.
   - It flagged the riskiest task (structured output) so we validated it early.
5. **We kept the spec in sync** as scope changed: we dropped the "ruled out" list, corrected the data size, and pinned the model.

**Compared with vibe coding:** the up-front questions caught decisions we hadn't made, and the data check caught the trial × site shape before any code was written. Each task ended in a demo, so a working app existed after every step instead of a big integration at the end.

### Steering docs (`.kiro/steering/`)

We had Kiro generate three steering files:

- **`product.md`:** the principles every change must keep — the LLM decides and the data supplies facts, no "qualify", exact English quotes, one question per turn, and a stateless server — plus the list rules enforced in `normalize`.
- **`tech.md`:** the stack, the exact build and test commands, environment variables, and conventions ("always run build + tests after changes", "no new deps without reason", "i18n strings live in `i18n.ts`").
- **`structure.md`:** a map of every backend and frontend file and the data flow.

**What made the biggest difference:** turning the product's safety rules into steering. Later sessions, such as UI polish, report formatting and the icons, kept the "looks like a fit" wording and the exact-quote rule without us repeating them. The commands in `tech.md` meant Kiro ran `pytest` and the Vitest suite on its own after edits.

### Iterating with Kiro CLI

- **Debugging.** We pasted a `GraphRecursionError` traceback. Kiro traced it to the agent's step budget and raised the recursion limit and per-tool call limits.
- **Understanding the code.** We asked how the agent remembers the trials it tracks across turns. Kiro explained the stateless design: the browser resends the previous lists, and the server turns them into a compact summary for the model.
- **Evaluation set.** Kiro read the trial CSV and wrote 20 persona prompts, each aimed at a specific trial, into [`kiro_prompts.tsv`](kiro_prompts.tsv). They cover rare cancers, pediatric epilepsy, healthy volunteers, IVF and more, and we use them to check that the agent finds the expected NCT ID. The agent found the target trial in 19 of 20 cases (95%).
- **Design polish.** Kiro made the SVG logo and favicon, matched the font sizes to US government-site standards, added the wave-dot "searching" animation, and added dividers and larger study titles to the report.

### Agent hooks, MCP, PBT, Powers

TODO — none in use yet. Either add them (below) or leave this section out:

- **Hook:** on save of `backend/**/*.py`, run `uv run pytest -q`; on save of `frontend/src/**`, run `npm test -- --run`.
- **Hook:** when `schemas.py` changes, check that `frontend/src/types.ts` still matches.
- **PBT** (Hypothesis): `normalize` never leaves a fit item with an unmet or unknown criterion; every closer-look item has a question; synonym expansion never matches "MI" inside "migraine".
- **MCP:** a fetch or ClinicalTrials.gov MCP server to refresh the snapshot.

## Testing instructions

**Live:** TODO URL. No login. Click a persona button, or type something like "I'm 54 with type 2 diabetes in Boston". Answer the questions, then click **All done**.

**Local:**

```bash
cp .env.example .env   # set OPENROUTER_API_KEY
cd frontend && npm install && npm run build && cd ..
cd backend && uv sync && uv run uvicorn app.main:app --port 8000
# open http://localhost:8000
```

Or use Docker: `docker build -t trialmatch . && docker run -p 8000:8000 --env-file .env trialmatch`

**Tests:** `cd backend && uv run pytest -q` · `cd frontend && npm test -- --run`

## Demo video outline (<3 min)

1. (0:00–0:20) The problem: registry filters, reading level, the 7% vs 55% gap.
2. (0:20–1:30) A persona chat: the lists update, a question is answered with a button, and a trial moves between lists. Open the drawer to show the verified quotes, sites and CMS rating.
3. (1:30–1:50) The map view, then a switch to Spanish with plain-language mode on.
4. (1:50–2:20) **All done**, then the report and an outreach email. Show the 95% recall result (19/20).
5. (2:20–2:55) Kiro: the brief, Kiro's questions, `plan_kiro.md`, the steering docs and the eval prompts.

Use no copyrighted music.

## Before submitting

- [ ] Fill in the team, repo URL, video URL and live URL
- [ ] Make the repo public and confirm `.kiro/` is committed and not in `.gitignore` (it is tracked now)
- [ ] Commit the outstanding changes, including `submission.md` and `kiro_prompts.tsv`
- [ ] Decide what to do about hooks, MCP and PBT (add them, or drop the section)
- [ ] Fix the stale map colors in `.kiro/steering/structure.md` (it says green/amber; the app uses blue/gray)
