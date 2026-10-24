import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import SidePanel from "./components/SidePanel";
import SiteMap from "./components/SiteMap";
import { sitesToPins } from "./mapPins";
import type { Hospital, Site, Trial } from "./types";

// jsdom has no layout/canvas, so replace react-leaflet with plain elements.
const fitBounds = vi.fn();
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => null,
  useMap: () => ({ fitBounds }),
  CircleMarker: ({ children, center, pathOptions }: { children: ReactNode; center: number[]; pathOptions: { fillColor: string } }) => (
    <div data-testid="pin" data-center={center.join(",")} data-color={pathOptions.fillColor}>
      {children}
    </div>
  ),
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

const site = (over: Partial<Site> = {}): Site => ({
  facility: "Mass General",
  city: "Boston",
  zip: "02114",
  contact: "",
  lat: 42.36,
  lon: -71.07,
  hospital: null,
  ...over,
});

const trial = (id: string, sites: Site[]): Trial => ({
  nct_id: id,
  title: `Study ${id}`,
  phase: "PHASE2",
  conditions: "",
  summary: "",
  why: "",
  criteria: [],
  question: null,
  sites,
  url: "",
});

const hospital: Hospital = { name: "MGH", hospital_type: "Acute Care Hospitals", emergency: true, overall_rating: 5 };

describe("sitesToPins", () => {
  it("groups sites at the same coordinates across both lists and dedupes trials", () => {
    const a = trial("A", [site(), site({ facility: "MGH Annex" })]);
    const b = trial("B", [site({ hospital })]);
    const pins = sitesToPins([a], [b]);
    expect(pins).toHaveLength(1);
    expect(pins[0].trials.map((t) => t.trial.nct_id)).toEqual(["A", "B"]);
    expect(pins[0].facilities).toEqual(["Mass General", "MGH Annex"]);
    expect(pins[0].hospital).toBe(hospital);
  });

  it("colors by list: fit wins when a spot has both", () => {
    const fitOnly = trial("A", [site({ lat: 1, lon: 1 })]);
    const closerOnly = trial("B", [site({ lat: 2, lon: 2 })]);
    const both = trial("C", [site({ lat: 3, lon: 3 })]);
    const pins = sitesToPins([fitOnly, both], [closerOnly, trial("D", [site({ lat: 3, lon: 3 })])]);
    const color = (lat: number) => pins.find((p) => p.lat === lat)!.list;
    expect(color(1)).toBe("fit");
    expect(color(2)).toBe("closer");
    expect(color(3)).toBe("fit");
  });

  it("skips sites without coordinates and returns [] for no trials", () => {
    expect(sitesToPins([trial("A", [site({ lat: null, lon: null })])], [])).toEqual([]);
    expect(sitesToPins([], [])).toEqual([]);
  });
});

describe("SiteMap", () => {
  it("renders one colored pin per spot with popup trial buttons that open the drawer", async () => {
    const onSelect = vi.fn();
    const a = trial("A", [site({ hospital })]);
    const b = trial("B", [site({ lat: 42.27, lon: -71.8, facility: "UMass", city: "Worcester" })]);
    render(<SiteMap pins={sitesToPins([a], [b])} onSelect={onSelect} />);
    const pins = screen.getAllByTestId("pin");
    expect(pins).toHaveLength(2);
    expect(pins[0]).toHaveAttribute("data-color", "#20558a");
    expect(pins[1]).toHaveAttribute("data-color", "#6b7280");
    expect(within(pins[0]).getByText("Mass General")).toBeInTheDocument();
    expect(within(pins[0]).getByText("Emergency services")).toBeInTheDocument();
    expect(within(pins[1]).getByText("Worcester")).toBeInTheDocument();
    await userEvent.click(within(pins[1]).getByRole("button", { name: "Study B" }));
    expect(onSelect).toHaveBeenCalledWith(b);
    expect(fitBounds).toHaveBeenCalledWith([[42.36, -71.07], [42.27, -71.8]], expect.anything());
  });
});

describe("SidePanel tabs", () => {
  it("toggles between lists and map", async () => {
    render(<SidePanel fit={[trial("A", [site()])]} closer={[]} onSelect={() => {}} />);
    expect(screen.getByRole("region", { name: "Looks like a fit" })).toBeInTheDocument();
    expect(screen.queryByTestId("map")).toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: "Map" }));
    expect(screen.getByTestId("map")).toBeInTheDocument();
    expect(screen.getAllByTestId("pin")).toHaveLength(1);
    expect(screen.queryByRole("region", { name: "Looks like a fit" })).toBeNull();
    await userEvent.click(screen.getByRole("tab", { name: "Lists" }));
    expect(screen.getByRole("region", { name: "Looks like a fit" })).toBeInTheDocument();
  });
});
