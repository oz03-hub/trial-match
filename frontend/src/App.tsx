import { useEffect, useState } from "react";
import { sendChat } from "./api";
import Chat, { type Message } from "./components/Chat";
import SidePanel from "./components/SidePanel";
import TrialDrawer from "./components/TrialDrawer";
import Report from "./components/Report";
import Footer from "./components/Footer";
import { LANGUAGES } from "./i18n";
import type { ChatMessage, Language, Trial, TrialMatchResponse } from "./types";

const FALLBACK_ERROR =
  "Sorry, I couldn't reach the trial search right now. Please try again in a moment.";

/** What the model sees for an assistant turn: its message plus the question it asked. */
function historyText(r: TrialMatchResponse): string {
  return r.next_question ? `${r.assistant_message}\n\n${r.next_question.text}` : r.assistant_message;
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [last, setLast] = useState<TrialMatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Trial | null>(null);
  const [showReport, setShowReport] = useState(true);
  const [language, setLanguage] = useState<Language>("en");
  const [plainLanguage, setPlainLanguage] = useState(false);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  async function send(text: string, finish = false) {
    const content = text.trim();
    if (!content || loading) return;
    const userMsg: Message = { role: "user", text: content };
    const next = [...messages, userMsg];
    setMessages(next);
    setLoading(true);

    const history: ChatMessage[] = next.map((m) => ({ role: m.role, content: m.history ?? m.text }));
    let reply: Message;
    try {
      const res = await sendChat({ messages: history, previous: last, finish, language, plain_language: plainLanguage });
      reply = { role: "assistant", text: res.assistant_message, history: historyText(res), warning: res.error };
      if (!res.error) {
        setLast(res);
        setShowReport(true);
      }
    } catch {
      reply = { role: "assistant", text: FALLBACK_ERROR, warning: true };
    }
    setMessages((m) => [...m, reply]);
    setLoading(false);
  }

  const report = last?.done && last.final_report_markdown ? last.final_report_markdown : null;

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 lg:h-screen print:h-auto">
      <header className="no-print border-b border-slate-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="flex items-center gap-2 text-lg font-semibold text-nih-800">
              <img src="/logo.svg" alt="" aria-hidden="true" className="h-7 w-7" />
              TrialMatch
            </h1>
            <p className="text-sm text-slate-600">Find recruiting clinical trials in Massachusetts</p>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <label className="flex items-center gap-2">
              Language
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as Language)}
                className="rounded-md border border-slate-300 bg-white px-2 py-1 focus:border-nih-600 focus:outline-none focus:ring-2 focus:ring-nih-600"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={plainLanguage}
                onChange={(e) => setPlainLanguage(e.target.checked)}
                className="h-4 w-4 accent-nih-700"
              />
              Plain language
            </label>
            {messages.length > 0 && <span className="text-xs text-slate-500">Changes apply from your next message.</span>}
          </div>
        </div>
      </header>
      <main className="mx-auto grid w-full max-w-7xl flex-1 gap-4 p-4 lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)] print:block">
        <Chat
          messages={messages}
          nextQuestion={last && !last.done ? last.next_question : null}
          loading={loading}
          language={language}
          canFinish={last !== null}
          onSend={(t) => send(t)}
          onFinish={() => send("All done — show my report", true)}
        />
        {report && showReport ? (
          <Report markdown={report} onBack={() => setShowReport(false)} />
        ) : (
          <SidePanel
            fit={last?.looks_like_a_fit ?? []}
            closer={last?.worth_a_closer_look ?? []}
            onSelect={setSelected}
            language={language}
            onShowReport={report ? () => setShowReport(true) : undefined}
          />
        )}
      </main>
      <Footer />
      {selected && <TrialDrawer trial={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
