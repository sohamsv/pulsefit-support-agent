import Link from "next/link";
import { PLANS } from "@/lib/content";

export const metadata = { title: "Plans | PulseFit Gym" };

export default function Plans() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-14">
      <h1 className="text-4xl font-extrabold tracking-tight">Plans and pricing</h1>
      <p className="mt-3 max-w-2xl text-muted">All plans include the gym floor and group classes. A one-time ₹999 joining fee applies, and it is waived on yearly plans.</p>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {PLANS.map((p) => (
          <div key={p.id} className={`flex flex-col rounded-xl border bg-surface p-6 ${p.highlight ? "border-accent" : "border-line"}`}>
            {p.highlight && <span className="mb-2 w-fit rounded-full bg-accent px-2 py-0.5 text-xs font-bold text-accentfg">Popular</span>}
            <h2 className="text-lg font-semibold">{p.name}</h2>
            <p className="mt-2 text-4xl font-extrabold">{p.price}</p>
            <p className="text-sm text-muted">{p.per}</p>
            <ul className="mt-5 flex-1 space-y-2 text-sm">
              {p.points.map((x) => (
                <li key={x} className="flex gap-2"><span className="text-accent" aria-hidden="true">✓</span>{x}</li>
              ))}
            </ul>
            <Link href="/trial" className="mt-6 rounded-lg border border-line px-4 py-2 text-center text-sm font-semibold hover:border-accent hover:text-accent">Try it free first</Link>
          </div>
        ))}
      </div>

      <div className="mt-12 grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-xl font-bold">Personal training</h2>
          <p className="mt-2 text-muted">From ₹4,000 for 12 sessions. Book a free consultation with a trainer first. Personal diet plans come with personal training.</p>
        </div>
        <div className="rounded-xl border border-line bg-surface p-6">
          <h2 className="text-xl font-bold">Payments</h2>
          <p className="mt-2 text-muted">We accept UPI and cards. EMI is available on yearly plans with select banks. Monthly plans renew on their own: turn auto-renewal off in the app at least 2 days before the renewal date.</p>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-line bg-surface p-6">
        <h2 className="text-xl font-bold">Freezing, cancelling and transferring</h2>
        <ul className="mt-3 space-y-2 text-muted">
          <li>Quarterly plans can be frozen up to 15 days and yearly plans up to 45 days, with 3 days&apos; notice.</li>
          <li>Monthly plans can be cancelled before the renewal date.</li>
          <li>Quarterly and yearly plans are not refundable after 7 days.</li>
          <li>A membership can be transferred once, for ₹500, if more than 30 days are left.</li>
          <li>Yearly members can use all branches and get 4 guest passes a year. Others use their home branch.</li>
        </ul>
      </div>
    </div>
  );
}
