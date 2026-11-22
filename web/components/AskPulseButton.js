"use client";

export default function AskPulseButton({ children = "Ask Pulse", className = "" }) {
  return (
    <button
      type="button"
      onClick={() => window.dispatchEvent(new Event("pulse:open"))}
      className={className || "rounded-lg border border-line px-5 py-3 font-semibold hover:border-accent hover:text-accent"}
    >
      {children}
    </button>
  );
}
