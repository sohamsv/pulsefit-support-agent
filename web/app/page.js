import Link from "next/link";
import AskPulseButton from "@/components/AskPulseButton";
import { PulseMark } from "@/components/Header";
import { CLASSES, FACILITIES, FAQS, PLANS } from "@/lib/content";

const STATS = [
  ["5 AM to 11 PM", "Open on weekdays"],
  ["5 class types", "Zumba to strength"],
  ["3 branches", "Panjim, Margao, Mapusa"],
  ["Free 1-day pass", "Try before you join"],
];

export default function Home() {
  return (
    <>
      <section className="mx-auto max-w-6xl px-4 pb-10 pt-16 sm:pt-24">
        <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1 text-xs font-medium text-muted">
          <span className="text-accent"><PulseMark className="h-4 w-4" /></span> Group classes · Personal training · Flexible plans
        </p>
        <h1 className="max-w-3xl text-5xl font-extrabold leading-[1.05] tracking-tight sm:text-7xl">
          Train with a <span className="text-accent">pulse.</span>
        </h1>
        <p className="mt-6 max-w-xl text-lg text-muted">
          PulseFit is the gym that keeps up with your week. Pick a plan, join a class, and ask Pulse, our support assistant, anything along the way.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/trial" className="rounded-lg bg-accent px-6 py-3 font-semibold text-accentfg hover:opacity-90">Book a free trial</Link>
          <Link href="/plans" className="rounded-lg border border-line px-6 py-3 font-semibold hover:border-accent hover:text-accent">See plans</Link>
          <AskPulseButton>Ask Pulse</AskPulseButton>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4" aria-label="Highlights">
        <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line lg:grid-cols-4">
          {STATS.map(([t, s]) => (
            <div key={t} className="bg-surface p-5">
              <dt className="text-lg font-bold">{t}</dt>
              <dd className="mt-1 text-sm text-muted">{s}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mx-auto mt-20 max-w-6xl px-4">
        <div className="flex items-end justify-between">
          <h2 className="text-3xl font-bold tracking-tight">Plans that fit your pace</h2>
          <Link href="/plans" className="text-sm font-semibold text-accent hover:underline">All plan details</Link>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {PLANS.map((p) => (
            <div key={p.id} className={`rounded-xl border p-6 ${p.highlight ? "border-accent" : "border-line"} bg-surface`}>
              <p className="font-semibold text-muted">{p.name}</p>
              <p className="mt-2 text-4xl font-extrabold">{p.price}</p>
              <p className="text-sm text-muted">{p.per}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-sm text-muted">One-time joining fee of ₹999, waived on yearly plans.</p>
      </section>

      <section className="mx-auto mt-20 max-w-6xl px-4">
        <h2 className="text-3xl font-bold tracking-tight">Classes for every mood</h2>
        <div className="mt-6 flex flex-wrap gap-2">
          {CLASSES.map((c) => (
            <Link key={c.name} href="/classes" className="rounded-full border border-line bg-surface px-4 py-2 text-sm font-medium hover:border-accent hover:text-accent">{c.name}</Link>
          ))}
        </div>
      </section>

      <section className="mx-auto mt-20 max-w-6xl px-4">
        <h2 className="text-3xl font-bold tracking-tight">Everything you need on site</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FACILITIES.map((f) => (
            <div key={f.title} className="rounded-xl border border-line bg-surface p-5">
              <p className="font-semibold">{f.title}</p>
              <p className="mt-2 text-sm text-muted">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto mt-20 max-w-3xl px-4">
        <h2 className="text-3xl font-bold tracking-tight">Quick answers</h2>
        <div className="mt-6 divide-y divide-line rounded-xl border border-line bg-surface">
          {FAQS.map((f) => (
            <details key={f.q} className="group p-4">
              <summary className="cursor-pointer list-none font-medium marker:content-none">{f.q}</summary>
              <p className="mt-2 text-sm text-muted">{f.a}</p>
            </details>
          ))}
        </div>
        <p className="mt-4 text-sm text-muted">Something else? <AskPulseButton className="font-semibold text-accent underline">Ask Pulse</AskPulseButton></p>
      </section>
    </>
  );
}
