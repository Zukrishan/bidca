// Vehicles-only features (FR-30, Q008). Shared with the transaction page (Phase 9c).

export const VEHICLES_CATEGORY = "Vehicles";

/** Static printable PDF in web/public — placeholder content until the client sends the real checklist. */
export const VEHICLE_CHECKLIST_URL = "/vehicle-inspection-checklist.pdf";

export function isVehicleListing(listing) {
  return listing?.category === VEHICLES_CATEGORY;
}

const yesNo = (v) => (v === true ? "Yes" : v === false ? "No" : "—");

/** [label, value] rows for the seller's vehicle disclosure, in the order the source lists them. */
export function disclosureRows(d) {
  if (!d) return [];
  return [
    ["Accident history", d.accident_history ? `Yes — ${d.accident_description || "no details given"}` : yesNo(d.accident_history)],
    ["Known mechanical issues", d.mechanical_issues ? `Yes — ${d.mechanical_description || "no details given"}` : yesNo(d.mechanical_issues)],
    ["Previous owners", d.previous_owners ?? "—"],
    ["Inspection / safety certificate", yesNo(d.safety_certificate)],
    ["Odometer", d.odometer_km != null ? `${Number(d.odometer_km).toLocaleString("en-CA")} km` : "—"],
    ["Liens or loans outstanding", yesNo(d.liens)],
  ];
}

const FIELD_LABELS = { year: "Year", make: "Make", model: "Model", mileage: "Mileage (km)", brand: "Brand" };

/** [label, value] rows for category_fields (Vehicles: year/make/model/mileage; Electronics: brand/model). */
export function categoryFieldRows(fields) {
  return Object.entries(fields || {})
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => [FIELD_LABELS[k] || k, k === "mileage" ? Number(v).toLocaleString("en-CA") : v]);
}
