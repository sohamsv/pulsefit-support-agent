import Link from "next/link";
import { CLASSES } from "@/lib/content";

export const metadata = { title: "Classes | PulseFit Gym" };

export default function Classes() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-14">
      <h1 className="text-4xl font-extrabold tracking-tight">Group classes</h1>
      <p className="mt-3 max-w-2xl text-muted">
        Zumba, yoga, HIIT, spin and strength, all included in every plan. The weekly schedule lives in the PulseFit app.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CLASSES.map((c) => (
          <article key={c.name} className="rounded-xl border border-line bg-surface p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold">{c.name}</h2>
              <span className="rounded-full border border-line px-2 py-0.5 text-xs text-muted">{c.tag}</span>
            </div>
            <p className="mt-3 text-sm text-muted">{c.blurb}</p>
            <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-accent">{c.level}</p>
          </article>
        ))}
      </div>

      <div className="mt-10 rounded-xl border border-line bg-surface p-6">
        <h2 className="text-xl font-bold">Booking rules</h2>
        <ul className="mt-3 space-y-2 text-muted">
          <li>Book in the app up to 2 days ahead.</li>
          <li>Can&apos;t make it? Cancel at least 2 hours before.</li>
          <li>Wear sports clothes and clean indoor shoes. Outdoor shoes are not allowed on the gym floor.</li>
          <li>Have a health condition? Get your doctor&apos;s clearance first and tell the trainer before you start.</li>
        </ul>
        <Link href="/trial" className="mt-5 inline-block rounded-lg bg-accent px-5 py-2 font-semibold text-accentfg">Book your free 1-day pass</Link>
      </div>
    </div>
  );
}
