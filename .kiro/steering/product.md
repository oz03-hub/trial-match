# Product

TrialMatch helps patients find recruiting Massachusetts clinical trials by conversation
instead of registry filters. A patient describes themselves in plain language; an LLM
agent searches public trial records over several rounds and sorts them into two live
lists: **Looks like a fit** and **Worth a closer look**. It asks one clarifying question
per turn (with suggested-answer buttons). Clicking **All done** produces a markdown
report of recruiting sites and contacts.

## Core principles

- **The LLM decides; the data layer supplies the facts.** The model only outputs trial
  ids, per-criterion judgments (met/unmet/unknown plus a quoted eligibility line), and
  questions. Contacts, sites, and links always come from the CSV so they cannot be
  hallucinated. The report is generated in code, not by the LLM.
- **Not medical advice.** The study coordinator always makes the final eligibility
  decision. Say "looks like a fit", never "qualify".
- **Quote exactly.** Eligibility quotes stay in the original English so they can be
  verified, even when the UI is translated.
- **One question per turn.** Each question is chosen to settle an open criterion.
- **Stateless server, state in the browser.** No accounts, no database, nothing stored
  server-side.

## List rules (enforced in `service.normalize`)

- A fit item with any `unmet` or `unknown` criterion moves to closer-look.
- Every closer-look item carries a resolving question.
- Each quote is checked against the trial's real eligibility text and gets
  `quote_verified`.
