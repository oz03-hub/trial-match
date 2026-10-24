import { useEffect, useRef } from "react";
import type { CriterionStatus, Trial } from "../types";
import HospitalInfo from "./HospitalInfo";

const PHASES: Record<string, string> = {
  EARLY_PHASE1: "Early Phase 1: a very small first-in-human study, mainly checking how the body handles the treatment.",
  PHASE1: "Phase 1: tests safety and dosing in a small group of people.",
  PHASE2: "Phase 2: checks whether the treatment works and keeps watching safety, in a larger group.",
  PHASE3: "Phase 3: compares the treatment with the current standard of care in many people.",
  PHASE4: "Phase 4: studies an already-approved treatment to learn more about long-term use.",
  NA: "Not applicable: this study isn't testing a drug in phases (for example, a device, behavior, or observational study).",
};

export function explainPhase(phase: string): string {
  const parts = phase.toUpperCase().split(/[|,/\s]+/).filter(Boolean);
  if (parts.length === 0) return "Phase not listed.";
  if (parts.length === 2 && parts.every((p) => PHASES[p])) {
    const [a, b] = parts.map((p) => p.replace("PHASE", "Phase "));
    return `${a}/${b.replace("Phase ", "")} combined: starts by testing safety and dosing, then moves on to whether the treatment works.`;
  }
  return parts.map((p) => PHASES[p] ?? `${p}.`).join(" ");
}

const STATUS: Record<CriterionStatus, { icon: string; label: string; cls: string }> = {
  met: { icon: "✓", label: "Met", cls: "text-emerald-800 bg-emerald-50 border-emerald-300" },
  unmet: { icon: "✗", label: "Not met", cls: "text-rose-800 bg-rose-50 border-rose-300" },
  unknown: { icon: "?", label: "Unknown", cls: "text-amber-900 bg-amber-50 border-amber-300" },
};

function studyUrl(t: Trial): string {
  return t.url.startsWith("https://") ? t.url : `https://clinicaltrials.gov/study/${encodeURIComponent(t.nct_id)}`;
}

export default function TrialDrawer({ trial, onClose }: { trial: Trial; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => closeRef.current?.focus(), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-xl space-y-5 overflow-y-auto bg-white p-5 shadow-xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="drawer-title" className="text-lg font-semibold text-slate-900">{trial.title}</h2>
            <p className="text-sm text-slate-600">{trial.nct_id}{trial.conditions && ` · ${trial.conditions}`}</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md px-2 py-1 text-slate-600 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600"
          >
            ✕
          </button>
        </div>

        {trial.question && (
          <p className="rounded-md bg-nih-50 p-3 text-sm font-medium text-nih-900">Open question: {trial.question}</p>
        )}

        <section>
          <h3 className="font-semibold">What this study is about</h3>
          <p className="mt-1 text-sm leading-relaxed text-slate-700">{trial.summary}</p>
        </section>

        <section>
          <h3 className="font-semibold">Phase</h3>
          <p className="mt-1 text-sm text-slate-700">{explainPhase(trial.phase)}</p>
        </section>

        <section>
          <h3 className="font-semibold">Why it came up</h3>
          <p className="mt-1 text-sm text-slate-700">{trial.why}</p>
        </section>

        <section>
          <h3 className="font-semibold">Eligibility checklist</h3>
          <ul className="mt-2 space-y-3">
            {trial.criteria.map((c, i) => {
              const s = STATUS[c.status];
              return (
                <li key={i} className={`rounded-md border p-3 ${s.cls}`}>
                  <p className="text-sm font-medium">
                    <span aria-hidden="true">{s.icon} </span>
                    <span className="sr-only">{s.label}: </span>
                    {c.text} <span className="text-xs font-normal">({s.label})</span>
                  </p>
                  {c.quote && (
                    <blockquote className="mt-2 border-l-4 border-slate-300 bg-white/70 px-3 py-1 text-xs italic text-slate-700">
                      “{c.quote}”
                    </blockquote>
                  )}
                  {c.quote && !c.quote_verified && <p className="mt-1 text-xs text-slate-600">(quote not found in the eligibility text; check the trial page)</p>}
                </li>
              );
            })}
          </ul>
        </section>

        <section>
          <h3 className="font-semibold">Recruiting sites</h3>
          {trial.sites.length === 0 ? (
            <p className="mt-1 text-sm text-slate-600">No recruiting sites listed — check the study page.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {trial.sites.map((s, i) => (
                <li key={i} className="text-sm text-slate-700">
                  <span className="font-medium">{s.facility}</span> — {s.city}
                  {s.zip && ` ${s.zip}`}
                  <HospitalInfo hospital={s.hospital} />
                  {s.contact && <div className="text-xs text-slate-600">Contact: {s.contact}</div>}
                </li>
              ))}
            </ul>
          )}
        </section>

        <p className="rounded-md bg-nih-50 p-3 text-sm text-nih-900">
          Ask the study coordinator to confirm eligibility — only the study team can make the final call.
        </p>

        <a
          href={studyUrl(trial)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block font-medium text-nih-800 underline focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600"
        >
          View full study on ClinicalTrials.gov
        </a>
      </div>
    </div>
  );
}
