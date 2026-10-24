import type { Hospital } from "../types";

/** CMS hospital facts for a site. Renders nothing when the site isn't a CMS-rated hospital. */
export default function HospitalInfo({ hospital }: { hospital: Hospital | null }) {
  if (!hospital) return null;
  const r = hospital.overall_rating;
  return (
    <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-600">
      {r == null ? (
        <span>Rating not available</span>
      ) : (
        <span>
          <span role="img" aria-label={`${r} out of 5 stars`} className="text-amber-500">
            {"★".repeat(r)}
            {"☆".repeat(5 - r)}
          </span>{" "}
          {r}/5 <span className="text-slate-500">CMS overall rating</span>
        </span>
      )}
      <span>{hospital.hospital_type}</span>
      {hospital.emergency && (
        <span className="rounded bg-rose-50 px-1.5 py-0.5 font-medium text-rose-800">Emergency services</span>
      )}
    </div>
  );
}
