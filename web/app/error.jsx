"use client";

export default function Error({ reset }) {
  return (
    <div className="flex flex-col items-start gap-3 py-12">
      <h1 className="text-2xl font-bold tracking-tight">Something went wrong</h1>
      <p className="text-muted-foreground">
        The listings service may be temporarily unavailable. Please try again in a moment.
      </p>
      <button
        type="button"
        onClick={() => reset()}
        className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium hover:bg-muted"
      >
        Try again
      </button>
    </div>
  );
}
