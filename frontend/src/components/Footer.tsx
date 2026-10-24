const LINKS = [
  { href: "https://clinicaltrials.gov", label: "ClinicalTrials.gov" },
  { href: "https://www.nih.gov/health-information/nih-clinical-research-trials-you", label: "NIH: clinical trials and you" },
  { href: "https://www.cancer.gov/about-cancer/treatment/clinical-trials", label: "NCI: cancer clinical trials" },
  { href: "https://medlineplus.gov/clinicaltrials.html", label: "MedlinePlus: clinical trials" },
];

export default function Footer() {
  return (
    <footer className="no-print border-t border-slate-300 bg-slate-200 px-4 py-3 text-xs text-slate-700">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <p className="max-w-3xl">
          TrialMatch is not medical advice and does not confirm eligibility. Matches come from an AI reading public trial
          records and can be wrong. Talk to your doctor and the study coordinator before deciding.
        </p>
        <nav aria-label="Clinical trial resources">
          <ul className="flex flex-wrap gap-x-4 gap-y-1">
            {LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline hover:text-nih-800 focus:outline-none focus:ring-2 focus:ring-nih-600"
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
