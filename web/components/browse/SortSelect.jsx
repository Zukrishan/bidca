"use client";

/** Sort dropdown that belongs to the filters form; auto-submits with JS, uses Apply without. */
export function SortSelect({ formId, value, options }) {
  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      Sort by
      <select
        name="sort"
        form={formId}
        defaultValue={value}
        onChange={(e) => e.target.form?.requestSubmit()}
        className="h-11 rounded-lg border border-border bg-surface px-3 text-base text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {options.map(([v, label]) => (
          <option key={v} value={v}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}
