"use client";
import { useCallback, useEffect, useState } from "react";
import { api, store } from "@/lib/api";

const field = "rounded-lg border border-line bg-bg px-3 py-2 text-sm";
const STATUS_LABEL = { open: "Open", in_progress: "In progress", resolved: "Resolved" };

function Tile({ label, value, tone }) {
  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-3xl font-extrabold ${tone || ""}`}>{value}</p>
    </div>
  );
}

function TicketCard({ t, token, onChange, onAuthLost }) {
  const [notes, setNotes] = useState(t.notes || "");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  async function patch(body) {
    setSaving(true);
    setErr("");
    try {
      await api(`/tickets/${t.ticket_id}`, { method: "PATCH", body, token });
      await onChange();
    } catch (e) {
      if (e.status === 401) onAuthLost();
      else setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  const high = t.priority === "high";
  return (
    <article className={`rounded-xl border bg-surface p-4 ${high && t.status !== "resolved" ? "border-danger/70" : "border-line"}`}>
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-bold">{t.ticket_id}</h3>
        <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${high ? "border-danger text-danger" : "border-line text-muted"}`}>{high ? "HIGH" : "normal"}</span>
        <span className="rounded-full bg-surface2 px-2 py-0.5 text-xs">{t.reason}</span>
        <span className="ml-auto text-xs text-muted">{t.time}</span>
      </div>
      <p className="mt-3 text-sm">“{t.message}”</p>
      <div className="mt-4 flex flex-wrap items-start gap-3">
        <label className="text-xs text-muted">Status
          <select className={`${field} mt-1 block`} value={t.status} disabled={saving} onChange={(e) => patch({ status: e.target.value })}>
            {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label className="min-w-48 flex-1 text-xs text-muted">Internal notes
          <textarea className={`${field} mt-1 block w-full`} rows={2} maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <button
          disabled={saving || notes === (t.notes || "")}
          onClick={() => patch({ notes })}
          className="self-end rounded-lg border border-line px-3 py-2 text-sm font-semibold hover:border-accent disabled:opacity-40"
        >
          {saving ? "Saving…" : "Save notes"}
        </button>
      </div>
      {err && <p role="alert" className="mt-2 text-sm text-danger">{err}</p>}
    </article>
  );
}

const TAG_LABEL = {
  core: "Core behaviors",
  tickets2: "Richer tickets",
  clarify: "Clarifying questions",
  lang: "Languages",
};

function QualityPanel({ evals }) {
  if (evals === undefined) {
    return (
      <section aria-labelledby="quality" className="mt-10 rounded-xl border border-line bg-surface p-5">
        <h2 id="quality" className="text-xl font-bold">Agent quality</h2>
        <p className="mt-2 text-sm text-muted">Loading…</p>
      </section>
    );
  }
  if (!evals?.available) {
    return (
      <section aria-labelledby="quality" className="mt-10 rounded-xl border border-line bg-surface p-5">
        <h2 id="quality" className="text-xl font-bold">Agent quality</h2>
        <p className="mt-2 text-sm text-muted">No test results saved yet. Run <code>python evals/run_evals.py --save</code> and redeploy to show them here.</p>
      </section>
    );
  }
  const pct = evals.total ? Math.round((evals.passed / evals.total) * 100) : 0;
  const groups = Object.entries(evals.by_tag || {}).filter(([t]) => TAG_LABEL[t]);
  const failing = (evals.cases || []).filter((c) => !c.passed);
  return (
    <section aria-labelledby="quality" className="mt-10 rounded-xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 id="quality" className="text-xl font-bold">Agent quality</h2>
        <p className="text-xs text-muted">Last test run: {evals.run_at} · took {Math.round((evals.duration_s || 0) / 60)} min · saved results, not run live</p>
      </div>
      <div className="mt-4 grid gap-6 md:grid-cols-[auto_1fr]">
        <div>
          <p className={`text-5xl font-extrabold ${pct === 100 ? "text-ok" : pct >= 80 ? "text-warn" : "text-danger"}`}>{pct}%</p>
          <p className="mt-1 text-sm text-muted">{evals.passed} of {evals.total} checks passed</p>
        </div>
        <ul className="space-y-3">
          {groups.map(([tag, d]) => {
            const p = d.total ? Math.round((d.passed / d.total) * 100) : 0;
            return (
              <li key={tag}>
                <div className="flex justify-between text-sm"><span>{TAG_LABEL[tag]}</span><span className="text-muted">{d.passed}/{d.total}</span></div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface2" role="progressbar" aria-label={TAG_LABEL[tag]} aria-valuenow={p} aria-valuemin={0} aria-valuemax={100}>
                  <div className="h-full bg-accent" style={{ width: `${p}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      </div>
      <div className="mt-5">
        <h3 className="text-sm font-semibold">{failing.length === 0 ? "No failing checks" : `Failing checks (${failing.length})`}</h3>
        <ul className="mt-2 space-y-2 text-sm">
          {failing.map((c) => (
            <li key={c.id} className="rounded-lg border border-line bg-bg p-3">
              <p className="font-semibold">{c.id}</p>
              <p className="text-muted">Asked: “{c.question}”</p>
              <p className="text-danger">{(c.failures || []).join("; ")}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default function Staff() {
  const [token, setToken] = useState(null);
  const [pass, setPass] = useState("");
  const [loginErr, setLoginErr] = useState("");
  const [tickets, setTickets] = useState([]);
  const [stats, setStats] = useState(null);
  const [trials, setTrials] = useState([]);
  const [evals, setEvals] = useState(undefined); // undefined = still loading
  const [statusF, setStatusF] = useState("");
  const [prioF, setPrioF] = useState("");
  const [loadErr, setLoadErr] = useState("");

  const logout = useCallback(() => {
    store.del("staff_token");
    setToken(null);
    setTickets([]);
    setStats(null);
  }, []);

  const load = useCallback(async () => {
    if (!token) return;
    const q = new URLSearchParams();
    if (statusF) q.set("status", statusF);
    if (prioF) q.set("priority", prioF);
    try {
      const [t, s, tr, ev] = await Promise.all([
        api(`/tickets${q.toString() ? `?${q}` : ""}`, { token }),
        api("/staff/stats", { token }),
        api("/staff/trials", { token }),
        api("/staff/evals", { token }).catch(() => ({ available: false })),
      ]);
      setTickets(t.tickets);
      setStats(s);
      setTrials(tr.trials);
      setEvals(ev);
      setLoadErr("");
    } catch (e) {
      if (e.status === 401) logout();
      else setLoadErr(e.message);
    }
  }, [token, statusF, prioF, logout]);

  // Restore the saved login from sessionStorage after the page loads (browser-only storage).
  useEffect(() => {
    const t = store.get("staff_token");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (t) setToken(t);
  }, []);
  // Load tickets now, then refresh every 20 seconds while logged in.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    if (!token) return;
    const id = setInterval(load, 20000);
    return () => clearInterval(id);
  }, [load, token]);

  async function login(e) {
    e.preventDefault();
    setLoginErr("");
    try {
      const out = await api("/staff/login", { method: "POST", body: { passcode: pass } });
      store.set("staff_token", out.token);
      setToken(out.token);
      setPass("");
    } catch (err) {
      setLoginErr(err.message);
    }
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-md px-4 py-14">
        <h1 className="text-4xl font-extrabold tracking-tight">Staff dashboard</h1>
        <p className="mt-3 text-muted">PulseFit team only. Enter the staff passcode.</p>
        <form onSubmit={login} className="mt-8 space-y-4 rounded-xl border border-line bg-surface p-6">
          <label className="block text-sm font-medium">Passcode
            <input type="password" className={`${field} mt-1 w-full`} value={pass} onChange={(e) => setPass(e.target.value)} required autoComplete="current-password" />
          </label>
          {loginErr && <p role="alert" className="text-sm text-danger">{loginErr}</p>}
          <button className="w-full rounded-lg bg-accent px-4 py-3 font-semibold text-accentfg">Open dashboard</button>
        </form>
      </div>
    );
  }

  const st = stats?.tickets_by_status || {};
  const pr = stats?.tickets_by_priority || {};
  const openHigh = tickets.filter((t) => t.priority === "high" && t.status !== "resolved").length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-extrabold tracking-tight">Staff dashboard</h1>
        <div className="flex gap-2">
          <button onClick={load} className="rounded-lg border border-line px-3 py-2 text-sm hover:border-accent">Refresh</button>
          <button onClick={logout} className="rounded-lg border border-line px-3 py-2 text-sm hover:border-accent">Log out</button>
        </div>
      </div>
      {loadErr && <p role="alert" className="mt-3 text-sm text-danger">{loadErr}</p>}

      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
        <Tile label="Open" value={st.open || 0} />
        <Tile label="In progress" value={st.in_progress || 0} tone="text-warn" />
        <Tile label="Resolved" value={st.resolved || 0} tone="text-ok" />
        <Tile label="High priority (all)" value={pr.high || 0} tone={openHigh ? "text-danger" : ""} />
        <Tile label="Chats handled" value={stats?.total_chats ?? 0} />
      </div>

      <section className="mt-10" aria-labelledby="tix">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="tix" className="text-xl font-bold">Tickets</h2>
          <select aria-label="Filter by status" className={field} value={statusF} onChange={(e) => setStatusF(e.target.value)}>
            <option value="">All statuses</option>
            {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <select aria-label="Filter by priority" className={field} value={prioF} onChange={(e) => setPrioF(e.target.value)}>
            <option value="">All priorities</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
          </select>
          <span className="text-sm text-muted">High priority first, resolved last. Updates every 20 seconds.</span>
        </div>
        <div className="mt-4 space-y-3">
          {tickets.length === 0 && <p className="rounded-xl border border-line bg-surface p-6 text-muted">No tickets match. Tickets raised by Pulse show up here.</p>}
          {tickets.map((t) => <TicketCard key={`${t.ticket_id}-${t.updated_at}`} t={t} token={token} onChange={load} onAuthLost={logout} />)}
        </div>
      </section>

      <div className="mt-10 grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="gaps" className="rounded-xl border border-line bg-surface p-5">
          <h2 id="gaps" className="text-xl font-bold">Questions Pulse couldn&apos;t answer</h2>
          <p className="mt-1 text-sm text-muted">Gaps in the help docs. Add these answers to improve Pulse.</p>
          <ul className="mt-3 space-y-2 text-sm">
            {(stats?.docs_gaps || []).length === 0 && <li className="text-muted">None yet.</li>}
            {(stats?.docs_gaps || []).map((g) => (
              <li key={g.question} className="flex justify-between gap-3 border-b border-line pb-2"><span>{g.question}</span><span className="text-muted">×{g.n}</span></li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="top" className="rounded-xl border border-line bg-surface p-5">
          <h2 id="top" className="text-xl font-bold">Top questions</h2>
          <p className="mt-1 text-sm text-muted">What customers ask Pulse most. Phone numbers are never stored.</p>
          <ul className="mt-3 space-y-2 text-sm">
            {(stats?.top_questions || []).length === 0 && <li className="text-muted">No chats yet.</li>}
            {(stats?.top_questions || []).map((g) => (
              <li key={g.question} className="flex justify-between gap-3 border-b border-line pb-2"><span>{g.question}</span><span className="text-muted">×{g.n}</span></li>
            ))}
          </ul>
        </section>
      </div>

      <QualityPanel evals={evals} />

      <section className="mt-10" aria-labelledby="trials">
        <h2 id="trials" className="text-xl font-bold">Free trial bookings</h2>
        <div className="mt-3 overflow-x-auto rounded-xl border border-line bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-muted"><tr><th className="p-3">Name</th><th className="p-3">Phone</th><th className="p-3">Branch</th><th className="p-3">Date</th><th className="p-3">Booked</th></tr></thead>
            <tbody>
              {trials.length === 0 && <tr><td className="p-3 text-muted" colSpan={5}>No bookings yet.</td></tr>}
              {trials.map((r) => (
                <tr key={r.id} className="border-t border-line"><td className="p-3">{r.name}</td><td className="p-3">{r.phone}</td><td className="p-3">{r.branch}</td><td className="p-3">{r.preferred_date}</td><td className="p-3 text-muted">{r.created_at}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
