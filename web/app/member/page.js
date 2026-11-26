"use client";
import { useCallback, useEffect, useState } from "react";
import AskPulseButton from "@/components/AskPulseButton";
import { api, store } from "@/lib/api";

const field = "mt-1 w-full rounded-lg border border-line bg-bg px-3 py-2";
const MONTHS = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };

function parseDMY(s) {
  const [d, m, y] = s.split("-");
  return new Date(Number(y), MONTHS[m], Number(d));
}

function daysLeft(end) {
  const ms = parseDMY(end) - new Date(new Date().toDateString());
  return Math.round(ms / 86400000);
}

const BADGE = {
  Active: "border-ok text-ok",
  Frozen: "border-warn text-warn",
  Expired: "border-danger text-danger",
};

export default function Member() {
  const [token, setToken] = useState(null);
  const [me, setMe] = useState(null);
  const [form, setForm] = useState({ member_id: "", phone_last4: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (t) => {
    try {
      setMe(await api("/member/me", { token: t }));
    } catch {
      store.del("member_token");
      setToken(null);
      setMe(null);
    }
  }, []);

  // Restore the saved login from sessionStorage after the page loads (browser-only storage).
  useEffect(() => {
    const t = store.get("member_token");
    if (t) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setToken(t);
      load(t);
    }
  }, [load]);

  async function login(e) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const out = await api("/member/login", { method: "POST", body: form });
      store.set("member_token", out.token);
      setToken(out.token);
      await load(out.token);
      setForm({ member_id: "", phone_last4: "" });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    store.del("member_token");
    setToken(null);
    setMe(null);
  }

  if (token && me) {
    const left = daysLeft(me.end_date);
    return (
      <div className="mx-auto max-w-2xl px-4 py-14">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-extrabold tracking-tight">Hi, {me.member_name.split(" ")[0]}!</h1>
          <button onClick={logout} className="rounded-lg border border-line px-3 py-2 text-sm hover:border-accent">Log out</button>
        </div>

        <div className="mt-6 rounded-xl border border-line bg-surface p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm text-muted">Member ID {me.member_id}</p>
              <p className="mt-1 text-3xl font-extrabold">{me.plan} plan</p>
            </div>
            <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${BADGE[me.status] || "border-line"}`}>{me.status}</span>
          </div>
          <dl className="mt-6 grid grid-cols-2 gap-4 text-sm">
            <div><dt className="text-muted">Started</dt><dd className="mt-1 font-semibold">{me.start_date}</dd></div>
            <div><dt className="text-muted">Ends</dt><dd className="mt-1 font-semibold">{me.end_date}</dd></div>
          </dl>
          {me.status !== "Expired" && left >= 0 && <p className="mt-5 text-sm text-muted">{left === 0 ? "Your plan ends today." : `${left} day${left === 1 ? "" : "s"} left on this plan.`}</p>}
          {me.status === "Frozen" && <p className="mt-2 text-sm text-warn">Your membership is frozen. Ask Pulse about unfreezing.</p>}
        </div>

        {me.action_needed && (
          <div className="mt-4 rounded-xl border border-danger/60 bg-surface p-5" role="alert">
            <p className="font-semibold">{me.action_needed}</p>
            <p className="mt-1 text-sm text-muted">Tell Pulse you&apos;d like renewal help and it can raise a ticket for our team.</p>
            <AskPulseButton className="mt-3 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-accentfg">Get renewal help</AskPulseButton>
          </div>
        )}

        <p className="mt-6 text-sm text-muted">Questions about freezing, transfers or payments? <AskPulseButton className="font-semibold text-accent underline">Ask Pulse</AskPulseButton></p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <h1 className="text-4xl font-extrabold tracking-tight">Member portal</h1>
      <p className="mt-3 text-muted">Check your membership with your member ID and the last 4 digits of your phone number.</p>
      <form onSubmit={login} className="mt-8 space-y-4 rounded-xl border border-line bg-surface p-6">
        <label className="block text-sm font-medium">Member ID
          <input className={field} value={form.member_id} onChange={(e) => setForm({ ...form, member_id: e.target.value })} placeholder="PF1001" required maxLength={20} autoComplete="off" />
        </label>
        <label className="block text-sm font-medium">Last 4 digits of phone
          <input className={field} value={form.phone_last4} onChange={(e) => setForm({ ...form, phone_last4: e.target.value })} inputMode="numeric" pattern="\d{4}" maxLength={4} required autoComplete="off" />
        </label>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        <button disabled={loading} className="w-full rounded-lg bg-accent px-4 py-3 font-semibold text-accentfg disabled:opacity-60">{loading ? "Checking…" : "View my membership"}</button>
      </form>
      <p className="mt-4 text-xs text-muted">Practice site: try PF1001 with 3840. Five wrong tries lock the login for 15 minutes.</p>
    </div>
  );
}
