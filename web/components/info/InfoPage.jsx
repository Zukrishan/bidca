/**
 * Layout for the information pages (FR-33): How It Works, Terms, Privacy, About.
 * The wording is PLACEHOLDER — the BidCa team writes the real text before launch (Q014).
 * `sections` is [{ heading, body: string | string[] }].
 */
export function InfoPage({ title, intro, sections }) {
  return (
    <article className="mx-auto flex max-w-[760px] flex-col gap-8">
      <header className="flex flex-col gap-3">
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <PlaceholderNotice />
        {intro ? <p className="text-lg text-muted-foreground">{intro}</p> : null}
      </header>
      {sections.map((s) => (
        <section key={s.heading} className="flex flex-col gap-2">
          <h2 className="text-xl font-semibold">{s.heading}</h2>
          {(Array.isArray(s.body) ? s.body : [s.body]).map((p, i) => (
            <p key={i} className="leading-relaxed">{p}</p>
          ))}
        </section>
      ))}
    </article>
  );
}

export function PlaceholderNotice() {
  return (
    <p role="note" className="rounded-lg border border-caution/40 bg-caution/10 px-4 py-3 text-sm font-medium text-caution">
      Placeholder text — draft only. The BidCa team is writing the final version of this page before launch.
    </p>
  );
}
