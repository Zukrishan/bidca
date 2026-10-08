import { cva } from "class-variance-authority";

import { cn } from "@/lib/utils";

// Ported from frontend/src/components/ui/badge.jsx: small text-only pills.
const badgeVariants = cva("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium", {
  variants: {
    variant: {
      default: "border-border bg-surface text-foreground",
      success: "border-transparent bg-success/10 text-success",
      urgent: "border-transparent bg-urgent/10 text-urgent",
    },
  },
  defaultVariants: { variant: "default" },
});

function Badge({ className, variant, ...props }) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
