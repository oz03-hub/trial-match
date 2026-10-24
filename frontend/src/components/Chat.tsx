import { useEffect, useRef, useState, type FormEvent } from "react";
import { STRINGS } from "../i18n";
import type { Language, NextQuestion } from "../types";

export interface Message {
  role: "user" | "assistant";
  text: string;
  /** Content sent back to the API, if different from what's displayed. */
  history?: string;
  warning?: boolean;
}

interface Props {
  messages: Message[];
  nextQuestion: NextQuestion | null;
  loading: boolean;
  canFinish: boolean;
  onSend: (text: string) => void;
  onFinish: () => void;
  language?: Language;
}

const PERSONAS = [
  "62-year-old woman, early-stage breast cancer, Worcester",
  "54, type 2 diabetes, Boston",
  "70, had a heart attack last year, Springfield",
  "35, healthy volunteer, Cambridge",
  "Caregiver: my dad (78) has Alzheimer's, near Lowell",
];

const btn =
  "rounded-md px-3 py-2 text-sm font-medium focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";

export default function Chat({ messages, nextQuestion, loading, canFinish, onSend, onFinish, language = "en" }: Props) {
  const t = STRINGS[language];
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages.length, loading]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    onSend(draft);
    setDraft("");
  }

  const lastIsAssistant = messages.length > 0 && messages[messages.length - 1].role === "assistant";

  return (
    <section aria-label="Conversation" className="no-print flex min-h-[60vh] flex-col rounded-xl border border-slate-200 bg-white lg:h-full">
      <ol className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
        <li className="max-w-[90%] rounded-lg bg-nih-50 px-3 py-2 text-sm leading-relaxed text-slate-800">{t.intro}</li>
        {messages.length === 0 && (
          <li className="space-y-2">
            <p className="text-xs font-medium text-slate-600">Try an example:</p>
            <div className="flex flex-wrap gap-2">
              {PERSONAS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => onSend(p)}
                  className="rounded-full border border-nih-700 bg-white px-3 py-1.5 text-left text-xs text-nih-800 hover:bg-nih-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-nih-600"
                >
                  {p}
                </button>
              ))}
            </div>
          </li>
        )}
        {messages.map((m, i) => (
          <li
            key={i}
            className={
              m.role === "user"
                ? "ml-auto max-w-[85%] whitespace-pre-wrap rounded-lg bg-nih-700 px-3 py-2 text-sm text-white"
                : m.warning
                  ? "max-w-[90%] whitespace-pre-wrap rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
                  : "max-w-[90%] whitespace-pre-wrap rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-800"
            }
          >
            <span className="sr-only">{m.role === "user" ? "You: " : "TrialMatch: "}</span>
            {m.warning && <span aria-hidden="true">⚠ </span>}
            {m.text}
          </li>
        ))}
        {nextQuestion && lastIsAssistant && !loading && (
          <li className="max-w-[90%] space-y-2">
            <p className="text-sm font-medium text-slate-900">{nextQuestion.text}</p>
            <div className="flex flex-wrap gap-2">
              {nextQuestion.suggested_answers.map((a) => (
                <button
                  key={a}
                  type="button"
                  onClick={() => onSend(a)}
                  className={`${btn} border border-nih-700 bg-white text-nih-800 hover:bg-nih-50`}
                >
                  {a}
                </button>
              ))}
            </div>
          </li>
        )}
        {loading && <SearchingIndicator phrases={t.searching} />}
        <div ref={endRef} />
      </ol>
      <div className="space-y-2 border-t border-slate-200 p-3">
        <form onSubmit={submit} className="flex gap-2">
          <label htmlFor="chat-input" className="sr-only">
            Your message
          </label>
          <input
            id="chat-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={t.placeholder}
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-nih-600 focus:outline-none focus:ring-2 focus:ring-nih-600"
          />
          <button type="submit" disabled={loading || !draft.trim()} className={`${btn} bg-nih-700 text-white hover:bg-nih-800`}>
            Send
          </button>
        </form>
        <button
          type="button"
          onClick={onFinish}
          disabled={!canFinish || loading}
          className={`${btn} w-full border border-slate-300 bg-white text-slate-800 hover:bg-slate-50`}
        >
          {t.allDone}
        </button>
      </div>
    </section>
  );
}

/**
 * Loading indicator shown while the agent is working. Cycles through a set of
 * status phrases and shows three dots in a smooth wave so the wait feels alive and
 * hints at the multi-round search happening on the server.
 */
function SearchingIndicator({ phrases }: { phrases: string[] }) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
    if (phrases.length <= 1) return;
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % phrases.length);
    }, 2200);
    return () => clearInterval(id);
  }, [phrases]);

  const phrase = phrases[index] ?? phrases[0] ?? "";

  return (
    <li role="status" aria-live="polite" className="flex items-center gap-2 text-sm text-slate-500">
      <span className="flex items-center gap-1" aria-hidden="true">
        <span className="dot-wave h-1.5 w-1.5 rounded-full bg-nih-500 [animation-delay:-0.28s]" />
        <span className="dot-wave h-1.5 w-1.5 rounded-full bg-nih-500 [animation-delay:-0.14s]" />
        <span className="dot-wave h-1.5 w-1.5 rounded-full bg-nih-500" />
      </span>
      <span key={index} className="italic animate-[fadeIn_0.4s_ease-out]">
        {phrase}
      </span>
    </li>
  );
}
