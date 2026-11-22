"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { BRANCHES } from "@/lib/content";

const field = "mt-1 w-full rounded-lg border border-line bg-bg px-3 py-2";

export default function Trial() {
  const today = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({ name: "", phone: "", branch: BRANCHES[0], preferred_date: today });
  const [state, setState] = useState({ status: "idle", message: "" });
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    if (state.status === "loading") return;
    setState({ status: "loading", message: "" });
    try {
      const out = await api("/trial", { method: "POST", body: form });
      setState({ status: "done", message: out.message });
    } catch (err) {
      setState({ status: "error", message: err.message });
    }
  }

  if (state.status === "done") {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <div className="rounded-xl border border-accent bg-surface p-8" role="status">
          <h1 className="text-3xl font-extrabold">You&apos;re in! 💪</h1>
          <p className="mt-3 text-muted">{state.message}</p>
          <p className="mt-2 text-sm text-muted">One free 1-day pass per person. Book your class in the PulseFit app.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-14">
      <h1 className="text-4xl font-extrabold tracking-tight">Book a free trial</h1>
      <p className="mt-3 text-muted">One free 1-day pass per person. Bring a photo ID. Use made-up details only, this is a practice site.</p>

      <form onSubmit={submit} className="mt-8 space-y-4 rounded-xl border border-line bg-surface p-6">
        <label className="block text-sm font-medium">Full name
          <input className={field} value={form.name} onChange={set("name")} required minLength={2} maxLength={60} autoComplete="name" />
        </label>
        <label className="block text-sm font-medium">Phone number (10 digits)
          <input className={field} value={form.phone} onChange={set("phone")} required inputMode="numeric" pattern="\d{10}" maxLength={10} autoComplete="tel" />
        </label>
        <label className="block text-sm font-medium">Branch
          <select className={field} value={form.branch} onChange={set("branch")}>
            {BRANCHES.map((b) => <option key={b}>{b}</option>)}
          </select>
        </label>
        <label className="block text-sm font-medium">Preferred date
          <input type="date" className={field} value={form.preferred_date} min={today} onChange={set("preferred_date")} required />
        </label>
        {state.status === "error" && <p role="alert" className="text-sm text-danger">{state.message}</p>}
        <button disabled={state.status === "loading"} className="w-full rounded-lg bg-accent px-4 py-3 font-semibold text-accentfg disabled:opacity-60">
          {state.status === "loading" ? "Booking…" : "Book my free pass"}
        </button>
      </form>
    </div>
  );
}
