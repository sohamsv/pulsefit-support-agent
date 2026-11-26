"use client";
import { useEffect, useRef, useState } from "react";
import { api, store } from "@/lib/api";
import { PulseMark } from "./Header";

const GREETING = "Hey, I'm Pulse from PulseFit! How can I help you today?";
const SUGGESTIONS = ["Is there a joining fee?", "What are the gym timings?", "Can I freeze my membership?"];
const MIN_GAP_MS = 3000; // client-side pacing: the free Gemini tier is only ~15 requests a minute

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([{ role: "pulse", text: GREETING }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(0); // seconds left when the server says "slow down"
  const sessionRef = useRef(null);
  const lastSent = useRef(0);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    sessionRef.current = store.get("pulse_session");
    const openIt = () => setOpen(true);
    window.addEventListener("pulse:open", openIt);
    return () => window.removeEventListener("pulse:open", openIt);
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy, open]);

  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  useEffect(() => { if (open) inputRef.current?.focus(); }, [open]);

  async function send(text) {
    const msg = (text ?? input).trim();
    if (!msg || busy || wait > 0) return;
    if (Date.now() - lastSent.current < MIN_GAP_MS) {
      setWait(Math.ceil((MIN_GAP_MS - (Date.now() - lastSent.current)) / 1000));
      return;
    }
    lastSent.current = Date.now();
    setInput("");
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setBusy(true);
    try {
      const out = await api("/chat", { method: "POST", body: { message: msg, session_id: sessionRef.current || undefined } });
      sessionRef.current = out.session_id;
      store.set("pulse_session", out.session_id);
      setMessages((m) => [...m, { role: "pulse", text: out.reply, tickets: out.ticket_ids }]);
    } catch (e) {
      if (e.status === 429) {
        setWait(Math.min(Math.max(e.retryAfter || 10, 3), 60));
        setMessages((m) => [...m, { role: "system", text: e.message }]);
      } else {
        setMessages((m) => [...m, { role: "system", text: e.message || "Something went wrong. Please try again." }]);
      }
    } finally {
      setBusy(false);
    }
  }

  const disabled = busy || wait > 0;

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full bg-accent px-5 py-3 font-semibold text-accentfg shadow-lg transition-transform hover:scale-105"
          aria-label="Chat with Pulse"
        >
          <PulseMark className="h-5 w-5" /> Ask Pulse
        </button>
      )}
      {open && (
        <section
          className="fixed inset-x-3 bottom-3 z-50 flex h-[min(34rem,calc(100dvh-1.5rem))] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl sm:inset-x-auto sm:right-5 sm:bottom-5 sm:w-96"
          aria-label="Chat with Pulse"
        >
          <header className="flex items-center justify-between bg-accent px-4 py-3 text-accentfg">
            <div className="flex items-center gap-2 font-bold"><PulseMark className="h-5 w-5" /> Pulse <span className="text-xs font-medium opacity-80">PulseFit support</span></div>
            <button onClick={() => setOpen(false)} className="rounded px-2 py-1 text-sm font-semibold hover:bg-black/10" aria-label="Close chat">Close</button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-3 py-4" role="log" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                    m.role === "user" ? "bg-accent text-accentfg" : m.role === "system" ? "border border-warn/50 bg-surface2 text-warn" : "bg-surface2 text-fg"
                  }`}
                >
                  {m.text}
                  {m.tickets?.length > 0 && (
                    <div className="mt-2 inline-block rounded-md border border-line bg-bg px-2 py-1 text-xs font-semibold text-accent">
                      Ticket {m.tickets.join(", ")} raised
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && <div className="text-xs text-muted">Pulse is typing…</div>}
            {messages.length === 1 && !busy && (
              <div className="flex flex-wrap gap-2 pt-1">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)} className="rounded-full border border-line px-3 py-1 text-xs hover:border-accent hover:text-accent">{s}</button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(); }} className="border-t border-line p-3">
            {wait > 0 && <p className="mb-2 text-xs text-warn">Pulse needs a moment. You can send again in {wait}s.</p>}
            <div className="flex gap-2">
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                maxLength={500}
                placeholder="Ask about plans, classes, timings…"
                aria-label="Message"
                className="min-w-0 flex-1 rounded-lg border border-line bg-bg px-3 py-2 text-sm"
              />
              <button type="submit" disabled={disabled || !input.trim()} className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-accentfg disabled:opacity-50">
                Send
              </button>
            </div>
            <p className="mt-2 text-[11px] text-muted">Pulse is an AI helper. Never share card numbers or passwords.</p>
          </form>
        </section>
      )}
    </>
  );
}
