import type { ChatRequest, TrialMatchResponse } from "./types";

export async function sendChat(req: ChatRequest): Promise<TrialMatchResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as TrialMatchResponse;
}
