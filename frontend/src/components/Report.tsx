import { useState } from "react";
import Markdown, { type Components } from "react-markdown";

const components: Components = {
  a: ({ node: _node, ...props }) => (
    <a {...props} target="_blank" rel="noopener noreferrer" className="text-nih-800 underline" />
  ),
};

export default function Report({ markdown, onBack }: { markdown: string; onBack: () => void }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "trialmatch-report.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  const btn =
    "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600";

  return (
    <section aria-label="Your report" className="rounded-xl border border-slate-200 bg-white p-5 lg:h-full lg:overflow-y-auto print:h-auto print:overflow-visible print:border-0">
      <div className="no-print mb-4 flex flex-wrap gap-2">
        <button type="button" onClick={copy} className={btn}>{copied ? "Copied!" : "Copy"}</button>
        <button type="button" onClick={download} className={btn}>Download .md</button>
        <button type="button" onClick={() => window.print()} className={btn}>Print</button>
        <button type="button" onClick={onBack} className={btn}>Back to lists</button>
      </div>
      <article className="report text-sm leading-relaxed text-slate-800">
        <Markdown components={components}>{markdown}</Markdown>
      </article>
    </section>
  );
}
