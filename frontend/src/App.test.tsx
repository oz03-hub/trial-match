import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import TrialDrawer from "./components/TrialDrawer";
import Report from "./components/Report";
import type { Hospital, Site, Trial, TrialMatchResponse } from "./types";

export const site = (over: Partial<Site> = {}): Site => ({
  facility: "Mass General",
  city: "Boston",
  zip: "02114",
  contact: "Jane Doe, 617-555-0100",
  lat: 42.36,
  lon: -71.07,
  hospital: null,
  ...over,
});

const hospital = (over: Partial<Hospital> = {}): Hospital => ({
  name: "Mass General Hospital",
  hospital_type: "Acute Care Hospitals",
  emergency: true,
  overall_rating: 4,
  ...over,
});

const trial = (over: Partial<Trial> = {}): Trial => ({
  nct_id: "NCT00000001",
  title: "Diabetes Exercise Study",
  phase: "PHASE2",
  conditions: "Type 2 Diabetes",
  summary: "Tests whether walking helps blood sugar.",
  why: "You mentioned type 2 diabetes.",
  criteria: [
    { text: "Age 18-75", status: "met", quote: "Adults aged 18 to 75", quote_verified: true },
    { text: "HbA1c 7-10%", status: "unknown", quote: "HbA1c between 7% and 10%", quote_verified: false },
    { text: "No insulin", status: "unmet", quote: "Not currently using insulin", quote_verified: true },
  ],
  question: null,
  sites: [site()],
  url: "https://clinicaltrials.gov/study/NCT00000001",
  ...over,
});

const resp = (over: Partial<TrialMatchResponse> = {}): TrialMatchResponse => ({
  assistant_message: "Here is what I found.",
  looks_like_a_fit: [],
  worth_a_closer_look: [],
  next_question: null,
  done: false,
  final_report_markdown: null,
  error: false,
  ...over,
});

let fetchMock: ReturnType<typeof vi.fn>;
function queue(...responses: TrialMatchResponse[]) {
  for (const r of responses) fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(r), { status: 200 }));
}
const body = (call: number) => JSON.parse(fetchMock.mock.calls[call][1].body);

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

async function say(text: string) {
  await userEvent.type(screen.getByLabelText("Your message"), text);
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
}

describe("App", () => {
  it("renders intro, user and assistant messages", async () => {
    queue(resp({ assistant_message: "Thanks! Searching diabetes trials." }));
    render(<App />);
    expect(screen.getByText(/nothing you type is stored/i)).toBeInTheDocument();
    await say("I'm 54 with type 2 diabetes");
    expect(screen.getByText("I'm 54 with type 2 diabetes")).toBeInTheDocument();
    expect(await screen.findByText("Thanks! Searching diabetes trials.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/chat", expect.objectContaining({ method: "POST" }));
    expect(body(0)).toEqual({
      messages: [{ role: "user", content: "I'm 54 with type 2 diabetes" }],
      previous: null,
      finish: false,
      language: "en",
      plain_language: false,
    });
  });

  it("clicking a suggested answer sends it with previous response", async () => {
    const first = resp({
      assistant_message: "Found some trials.",
      worth_a_closer_look: [trial({ question: "Do you use insulin?" })],
      next_question: { text: "Do you currently use insulin?", suggested_answers: ["Yes", "No"] },
    });
    queue(first, resp());
    render(<App />);
    await say("diabetes");
    await userEvent.click(await screen.findByRole("button", { name: "No" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const b = body(1);
    expect(b.messages.at(-1)).toEqual({ role: "user", content: "No" });
    expect(b.messages[1]).toEqual({ role: "assistant", content: "Found some trials.\n\nDo you currently use insulin?" });
    expect(b.previous).toEqual(first);
    expect(b.finish).toBe(false);
  });

  it("moves a trial from closer-look to fit on a new response", async () => {
    const t = trial({ question: "Do you use insulin?" });
    queue(resp({ worth_a_closer_look: [t] }), resp({ looks_like_a_fit: [{ ...t, question: null }] }));
    render(<App />);
    await say("diabetes");
    const closer = await screen.findByRole("region", { name: "Worth a closer look" });
    expect(within(closer).getByText("Diabetes Exercise Study")).toBeInTheDocument();
    expect(within(closer).getByText("Do you use insulin?")).toBeInTheDocument();
    expect(screen.getByText("1 met · 1 unknown · 1 not met")).toBeInTheDocument();
    await say("no insulin");
    const fit = screen.getByRole("region", { name: "Looks like a fit" });
    expect(await within(fit).findByText("Diabetes Exercise Study")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Worth a closer look" })).queryByText("Diabetes Exercise Study")).toBeNull();
  });

  it("error response shows warning message and keeps lists", async () => {
    const good = resp({ looks_like_a_fit: [trial()] });
    queue(good, resp({ assistant_message: "Sorry, the search hit a snag.", error: true }), resp());
    render(<App />);
    await say("diabetes");
    await screen.findByText("Diabetes Exercise Study");
    await say("more");
    expect(await screen.findByText("Sorry, the search hit a snag.")).toBeInTheDocument();
    expect(screen.getByText("Diabetes Exercise Study")).toBeInTheDocument();
    await say("again");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    expect(body(2).previous).toEqual(good);
  });

  it("finish button sends finish:true and shows the report", async () => {
    queue(resp(), resp({ done: true, final_report_markdown: "# My trial report\n\n- NCT00000001" }));
    render(<App />);
    expect(screen.getByRole("button", { name: /all done/i })).toBeDisabled();
    await say("diabetes");
    await userEvent.click(await screen.findByRole("button", { name: /all done/i }));
    expect(await screen.findByRole("heading", { name: "My trial report" })).toBeInTheDocument();
    expect(body(1).finish).toBe(true);
  });

  it("sends language and plain_language, applying changes from the next turn", async () => {
    queue(resp(), resp());
    render(<App />);
    await say("hi");
    await screen.findByText("Here is what I found.");
    await userEvent.selectOptions(screen.getByLabelText("Language"), "es");
    await userEvent.click(screen.getByLabelText("Plain language"));
    expect(screen.getByText(/apply from your next message/i)).toBeInTheDocument();
    await say("more");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(body(0)).toMatchObject({ language: "en", plain_language: false });
    expect(body(1)).toMatchObject({ language: "es", plain_language: true });
  });

  it("translates the intro, placeholder, finish button and list headings", async () => {
    render(<App />);
    await userEvent.selectOptions(screen.getByLabelText("Language"), "es");
    expect(screen.getByText(/Nada de lo que escriba/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Escriba su respuesta o descríbase…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Listo/ })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Parece adecuado" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Vale la pena revisar" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("es");
  });

  it("persona chips send the first message and disappear afterwards", async () => {
    queue(resp());
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "54, type 2 diabetes, Boston" }));
    expect(await screen.findByText("Here is what I found.")).toBeInTheDocument();
    expect(body(0).messages).toEqual([{ role: "user", content: "54, type 2 diabetes, Boston" }]);
    expect(screen.queryByRole("button", { name: /Springfield/ })).toBeNull();
  });

  it("never uses the word 'qualify'", async () => {
    queue(resp({ looks_like_a_fit: [trial()], worth_a_closer_look: [trial({ nct_id: "NCT2", question: "Q?" })] }));
    render(<App />);
    await say("hi");
    await screen.findAllByText("Diabetes Exercise Study");
    expect(document.body.textContent).not.toMatch(/qualif/i);
  });
});

describe("TrialDrawer", () => {
  it("renders criterion statuses, quotes and study link", () => {
    render(<TrialDrawer trial={trial()} onClose={() => {}} />);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/Met:/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Unknown:/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Not met:/)).toBeInTheDocument();
    expect(within(dialog).getByText("“Adults aged 18 to 75”")).toBeInTheDocument();
    expect(within(dialog).getAllByText("(quote not found in the eligibility text; check the trial page)")).toHaveLength(1);
    expect(within(dialog).getByText(/Phase 2: checks whether/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Jane Doe/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Ask the study coordinator to confirm eligibility/)).toBeInTheDocument();
    expect(within(dialog).getByRole("link", { name: /ClinicalTrials.gov/ })).toHaveAttribute(
      "href",
      "https://clinicaltrials.gov/study/NCT00000001",
    );
  });

  it("shows CMS hospital rating, type and emergency badge", () => {
    const t = trial({ sites: [site({ hospital: hospital() })] });
    render(<TrialDrawer trial={t} onClose={() => {}} />);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByLabelText("4 out of 5 stars")).toHaveTextContent("★★★★☆");
    expect(within(dialog).getByText(/4\/5/)).toBeInTheDocument();
    expect(within(dialog).getByText("CMS overall rating")).toBeInTheDocument();
    expect(within(dialog).getByText("Acute Care Hospitals")).toBeInTheDocument();
    expect(within(dialog).getByText("Emergency services")).toBeInTheDocument();
  });

  it("handles missing rating, no emergency, and no hospital", () => {
    const t = trial({
      sites: [
        site({ hospital: hospital({ overall_rating: null, emergency: false }) }),
        site({ facility: "Local Clinic", hospital: null }),
      ],
    });
    render(<TrialDrawer trial={t} onClose={() => {}} />);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getAllByText("Rating not available")).toHaveLength(1);
    expect(within(dialog).queryByText("Emergency services")).toBeNull();
    expect(within(dialog).queryByText("CMS overall rating")).toBeNull();
    expect(within(dialog).getByText("Local Clinic")).toBeInTheDocument();
  });

  it("closes on Escape", async () => {
    const onClose = vi.fn();
    render(<TrialDrawer trial={trial()} onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});

describe("Report", () => {
  it("renders markdown but not raw HTML", () => {
    const md = "# Report\n\n**Bold** and [study](https://clinicaltrials.gov/study/NCT1)\n\n<script>window.hacked=1</script>\n\n<img src=x onerror=alert(1)>";
    const { container } = render(<Report markdown={md} onBack={() => {}} />);
    expect(screen.getByRole("heading", { name: "Report" })).toBeInTheDocument();
    expect(container.querySelector("strong")).toHaveTextContent("Bold");
    expect(screen.getByRole("link", { name: "study" })).toHaveAttribute("target", "_blank");
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect((window as unknown as { hacked?: number }).hacked).toBeUndefined();
  });

  it("renders email blockquotes and rules, and has a Download .md button", async () => {
    const md = "# R\n\n---\n\n> **Subject:** Hi\n>\n> Dear Study Team,";
    const createObjectURL = vi.fn(() => "blob:x");
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const { container } = render(<Report markdown={md} onBack={() => {}} />);
    expect(container.querySelector("blockquote")).toHaveTextContent("Dear Study Team,");
    expect(container.querySelector("hr")).not.toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Download .md" }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:x");
    click.mockRestore();
  });
});
