"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const LINKS = [
  { href: "/plans", label: "Plans" },
  { href: "/classes", label: "Classes" },
  { href: "/trial", label: "Free trial" },
  { href: "/member", label: "Member portal" },
];

export function PulseMark({ className = "h-6 w-6" }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" aria-hidden="true">
      <path d="M2 17h6l3-9 5 17 4-12 2 4h8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Header() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const link = (l) => (
    <Link
      key={l.href}
      href={l.href}
      onClick={() => setOpen(false)}
      aria-current={path === l.href ? "page" : undefined}
      className={`rounded-md px-3 py-2 text-sm font-medium transition-colors hover:text-accent ${path === l.href ? "text-accent" : "text-fg"}`}
    >
      {l.label}
    </Link>
  );
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold tracking-tight">
          <span className="text-accent"><PulseMark /></span>
          PulseFit
        </Link>
        <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
          {LINKS.map(link)}
          <Link href="/staff" className="ml-2 rounded-md border border-line px-3 py-2 text-sm text-muted hover:text-fg">Staff</Link>
        </nav>
        <button
          className="rounded-md border border-line px-3 py-2 text-sm md:hidden"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-label="Toggle menu"
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>
      {open && (
        <nav className="flex flex-col border-t border-line px-4 py-2 md:hidden" aria-label="Mobile">
          {LINKS.map(link)}
          <Link href="/staff" onClick={() => setOpen(false)} className="px-3 py-2 text-sm text-muted">Staff</Link>
        </nav>
      )}
    </header>
  );
}
