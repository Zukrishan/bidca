import { VEHICLE_CHECKLIST_URL, isVehicleListing } from "@/lib/vehicle";

/** "📋 Download Vehicle Inspection Checklist" — Vehicles listings only, no login (FR-30). Renders nothing otherwise. */
export function VehicleChecklistLink({ listing, className = "" }) {
  if (!isVehicleListing(listing)) return null;
  return (
    <a
      href={VEHICLE_CHECKLIST_URL}
      target="_blank"
      rel="noopener"
      download
      className={`inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-4 py-2.5 text-sm font-medium text-primary hover:underline ${className}`}
    >
      <span aria-hidden>📋</span> Download Vehicle Inspection Checklist
    </a>
  );
}
