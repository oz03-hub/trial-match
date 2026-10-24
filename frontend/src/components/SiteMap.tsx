import { useEffect } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import HospitalInfo from "./HospitalInfo";
import { PIN_COLORS, type Pin } from "../mapPins";
import type { Trial } from "../types";

const MA_CENTER: [number, number] = [42.25, -71.8];

function FitBounds({ pins }: { pins: Pin[] }) {
  const map = useMap();
  useEffect(() => {
    if (pins.length > 0) map.fitBounds(pins.map((p) => [p.lat, p.lon] as [number, number]), { padding: [30, 30], maxZoom: 12 });
  }, [map, pins]);
  return null;
}

export default function SiteMap({ pins, onSelect }: { pins: Pin[]; onSelect: (t: Trial) => void }) {
  return (
    <div className="isolate">
      <p className="mb-2 text-xs text-slate-600">
        <span style={{ color: PIN_COLORS.fit }} aria-hidden="true">●</span> Looks like a fit{" "}
        <span style={{ color: PIN_COLORS.closer }} aria-hidden="true">●</span> Worth a closer look
        {pins.length === 0 && " — no mappable sites yet."}
      </p>
      <MapContainer center={MA_CENTER} zoom={8} className="h-96 w-full rounded-lg lg:h-[calc(100vh-14rem)]">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds pins={pins} />
        {pins.map((p) => (
          <CircleMarker
            key={p.key}
            center={[p.lat, p.lon]}
            radius={9}
            pathOptions={{ color: "#fff", weight: 2, fillColor: PIN_COLORS[p.list], fillOpacity: 0.95 }}
          >
            <Popup>
              <div className="space-y-1 text-sm">
                <p className="font-medium">{p.facilities.join(" / ")}</p>
                <p className="text-xs text-slate-600">{p.city}</p>
                <HospitalInfo hospital={p.hospital} />
                <ul className="space-y-1 pt-1">
                  {p.trials.map(({ trial }) => (
                    <li key={trial.nct_id}>
                      <button
                        type="button"
                        onClick={() => onSelect(trial)}
                        className="text-left text-nih-800 underline"
                      >
                        {trial.title}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
