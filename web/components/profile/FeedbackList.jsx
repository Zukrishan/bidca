import { RATING_STYLES, RatingIcon } from "@/components/profile/Rating";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";

const ROLE = { buyer_to_seller: "from a buyer", seller_to_buyer: "from a seller" };

export function FeedbackList({ feedback }) {
  if (!feedback.length) {
    return <p className="text-muted-foreground">No feedback yet.</p>;
  }
  return (
    <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
      {feedback.map((f) => (
        <li key={f._id} className="flex flex-col gap-1 p-4">
          <div className="flex items-baseline justify-between gap-2 text-sm">
            <span className={cn("inline-flex items-center gap-1.5 font-medium", RATING_STYLES[f.rating]?.className)}>
              <RatingIcon rating={f.rating} className="self-center" />
              {RATING_STYLES[f.rating]?.label || f.rating}
              <span className="font-normal text-muted-foreground">
                {[ROLE[f.feedback_type], f.from_user_name ? `· ${f.from_user_name}` : ""].filter(Boolean).join(" ")}
              </span>
            </span>
            <span className="text-xs text-muted-foreground">{formatDate(f.created_at)}</span>
          </div>
          {f.comment ? <p className="text-sm">{f.comment}</p> : null}
        </li>
      ))}
    </ul>
  );
}
