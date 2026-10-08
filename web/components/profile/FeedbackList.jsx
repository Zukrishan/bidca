import { formatDate } from "@/lib/format";

const LABELS = { positive: "Positive", neutral: "Neutral", negative: "Negative" };

export function FeedbackList({ feedback }) {
  if (!feedback.length) {
    return <p className="text-muted-foreground">No feedback yet.</p>;
  }
  return (
    <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
      {feedback.map((f) => (
        <li key={f._id} className="flex flex-col gap-1 p-4">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className={f.rating === "positive" ? "font-medium text-success" : "font-medium"}>
              {LABELS[f.rating] || f.rating}
            </span>
            <span className="text-xs text-muted-foreground">{formatDate(f.created_at)}</span>
          </div>
          {f.comment ? <p className="text-sm">{f.comment}</p> : null}
        </li>
      ))}
    </ul>
  );
}
