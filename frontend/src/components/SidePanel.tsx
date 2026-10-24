import { useMemo, useState } from "react";
import { sitesToPins } from "../mapPins";
import { STRINGS } from "../i18n";
import type { Language, Trial } from "../types";
import SiteMap from "./SiteMap";

interface Props {
  fit: Trial[];
  closer: Trial[];
  onSelect: (t: Trial) => void;
  language?: Language;
  onShowReport?: () => void;
}

function statusSummary(t: Trial): string {
  const count = (s: string) => t.criteria.filter((c) => c.status === s).length;
  return `${count("met")} met · ${count("unknown")} unknown · ${count("unmet")} not met`;
}

function sitesSummary(t: Trial): string {
  if (t.sites.length === 0) return "No recruiting sites listed";
  const n = t.sites.length;
  return `${n} recruiting site${n === 1 ? "" : "s"} · ${t.sites[0].city}`;
}

function TrialCard({ trial, onSelect }: { trial: Trial; onSelect: (t: Trial) => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(trial)}
        className="w-full rounded-lg border border-slate-200 bg-white p-3 text-left hover:border-nih-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600"
      >
        {trial.question && (
          <p className="mb-2 rounded bg-nih-50 px-2 py-1 text-sm font-medium text-nih-900">{trial.question}</p>
        )}
        <p className="font-medium text-slate-900">{trial.title}</p>
        <p className="mt-1 text-xs text-slate-600">
          {trial.nct_id} · {trial.phase || "Phase not listed"} · {sitesSummary(trial)}
        </p>
        <p className="mt-1 text-xs text-slate-600">{statusSummary(trial)}</p>
      </button>
    </li>
  );
}

function List({ title, hint, trials, onSelect }: { title: string; hint: string; trials: Trial[]; onSelect: (t: Trial) => void }) {
  return (
    <section aria-label={title}>
      <h2 className="text-base font-semibold text-slate-900">
        {title} <span className="font-normal text-slate-500">({trials.length})</span>
      </h2>
      <p className="mb-2 text-xs text-slate-500">{hint}</p>
      {trials.length === 0 ? (
        <p className="text-sm text-slate-500">Nothing here yet.</p>
      ) : (
        <ul className="space-y-2">
          {trials.map((t) => (
            <TrialCard key={t.nct_id} trial={t} onSelect={onSelect} />
          ))}
        </ul>
      )}
    </section>
  );
}

type Tab = "lists" | "map";

export default function SidePanel({ fit, closer, onSelect, language = "en", onShowReport }: Props) {
  const [tab, setTab] = useState<Tab>("lists");
  const pins = useMemo(() => sitesToPins(fit, closer), [fit, closer]);
  const t = STRINGS[language];
  return (
    <aside className="no-print space-y-4 rounded-xl border border-slate-200 bg-slate-100/60 p-4 lg:h-full lg:overflow-y-auto">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div role="tablist" aria-label="View" className="inline-flex rounded-md border border-slate-300 bg-white p-0.5 text-sm">
          {(["lists", "map"] as const).map((k) => (
            <button
              key={k}
              type="button"
              role="tab"
              aria-selected={tab === k}
              onClick={() => setTab(k)}
              className={`rounded px-3 py-1 font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600 ${
                tab === k ? "bg-nih-700 text-white" : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {k === "lists" ? "Lists" : "Map"}
            </button>
          ))}
        </div>
        {onShowReport && (
          <button
            type="button"
            onClick={onShowReport}
            className="rounded-md bg-nih-700 px-3 py-2 text-sm font-medium text-white hover:bg-nih-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600 focus-visible:ring-offset-2"
          >
            View my report
          </button>
        )}
      </div>
      {tab === "map" ? (
        <SiteMap pins={pins} onSelect={onSelect} />
      ) : (
        <div className="space-y-6">
          <List title={t.fit} hint="Everything we could check lines up." trials={fit} onSelect={onSelect} />
          <List title={t.closer} hint="Promising — one open question could settle it." trials={closer} onSelect={onSelect} />
        </div>
      )}
      <p className="text-xs text-slate-500">Only the study team can confirm eligibility.</p>
    </aside>
  );
}
