import type { Hospital, Trial } from "./types";

export type PinList = "fit" | "closer";

export interface Pin {
  key: string;
  lat: number;
  lon: number;
  /** "fit" if any trial at this spot is a fit, else "closer". */
  list: PinList;
  facilities: string[];
  city: string;
  hospital: Hospital | null;
  trials: { trial: Trial; list: PinList }[];
}

export const PIN_COLORS: Record<PinList, string> = { fit: "#20558a", closer: "#6b7280" };

/** One pin per distinct coordinate, across both lists. Sites without lat/lon are skipped. */
export function sitesToPins(fit: Trial[], closer: Trial[]): Pin[] {
  const pins = new Map<string, Pin>();
  const add = (trial: Trial, list: PinList) => {
    for (const s of trial.sites) {
      if (s.lat == null || s.lon == null) continue;
      const key = `${s.lat.toFixed(4)},${s.lon.toFixed(4)}`;
      let pin = pins.get(key);
      if (!pin) {
        pin = { key, lat: s.lat, lon: s.lon, list, facilities: [], city: s.city, hospital: null, trials: [] };
        pins.set(key, pin);
      }
      if (list === "fit") pin.list = "fit";
      if (!pin.facilities.includes(s.facility)) pin.facilities.push(s.facility);
      pin.hospital ??= s.hospital;
      if (!pin.trials.some((t) => t.trial.nct_id === trial.nct_id)) pin.trials.push({ trial, list });
    }
  };
  fit.forEach((t) => add(t, "fit"));
  closer.forEach((t) => add(t, "closer"));
  return [...pins.values()];
}
