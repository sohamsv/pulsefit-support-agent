import Link from "next/link";
import { TIMINGS } from "@/lib/content";

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 text-sm sm:grid-cols-3">
        <div>
          <p className="text-base font-bold">PulseFit Gym</p>
          <p className="mt-2 max-w-xs text-muted">A made-up chain of gyms with group classes, personal training and flexible memberships.</p>
        </div>
        <div>
          <p className="font-semibold">Opening hours</p>
          <ul className="mt-2 space-y-1 text-muted">
            {TIMINGS.map((t) => (
              <li key={t.days}>{t.days}: {t.hours}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-semibold">Explore</p>
          <ul className="mt-2 space-y-1 text-muted">
            <li><Link className="hover:text-accent" href="/plans">Plans</Link></li>
            <li><Link className="hover:text-accent" href="/classes">Classes</Link></li>
            <li><Link className="hover:text-accent" href="/trial">Book a free trial</Link></li>
            <li><Link className="hover:text-accent" href="/member">Member portal</Link></li>
          </ul>
        </div>
      </div>
      <p className="border-t border-line px-4 py-4 text-center text-xs text-muted">
        PulseFit Gym is a made-up business. All data is practice data. No real customers.
      </p>
    </footer>
  );
}
