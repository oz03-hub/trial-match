// Mirror of backend/app/schemas.py (API layer). Keep in sync.

export type CriterionStatus = "met" | "unmet" | "unknown";

export interface Criterion {
  text: string;
  status: CriterionStatus;
  quote: string;
  quote_verified: boolean;
}

export interface Hospital {
  name: string;
  hospital_type: string;
  emergency: boolean;
  overall_rating: number | null;
}

export interface Site {
  facility: string;
  city: string;
  zip: string;
  contact: string;
  lat: number | null;
  lon: number | null;
  hospital: Hospital | null;
}

export type Language = "en" | "es" | "pt" | "zh" | "ht" | "vi";

export interface Trial {
  nct_id: string;
  title: string;
  phase: string;
  conditions: string;
  summary: string;
  why: string;
  criteria: Criterion[];
  question: string | null;
  sites: Site[];
  url: string;
}

export interface NextQuestion {
  text: string;
  suggested_answers: string[];
}

export interface TrialMatchResponse {
  assistant_message: string;
  looks_like_a_fit: Trial[];
  worth_a_closer_look: Trial[];
  next_question: NextQuestion | null;
  done: boolean;
  final_report_markdown: string | null;
  error: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  previous: TrialMatchResponse | null;
  finish: boolean;
  language: Language;
  plain_language: boolean;
}
