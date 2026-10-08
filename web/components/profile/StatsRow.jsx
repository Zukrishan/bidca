export function StatsRow({ stats }) {
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-4">
      {stats.map((s) => (
        <div key={s.label} className="flex flex-col gap-1 bg-surface p-4">
          <dd className="tabular text-xl font-semibold">{s.value}</dd>
          <dt className="text-xs text-muted-foreground">{s.label}</dt>
        </div>
      ))}
    </dl>
  );
}
