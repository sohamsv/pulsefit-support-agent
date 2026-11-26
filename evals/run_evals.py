"""Run Pulse through evals/cases.json and print a pass/fail table.

Usage (from the project root):
  python evals/run_evals.py --quick                # about 12 important cases
  python evals/run_evals.py --tags core            # one group (core, tickets2, clarify, lang, quick)
  python evals/run_evals.py --ids faq_joining_fee  # one or more cases
  python evals/run_evals.py --save                 # full run, writes evals/results.json (shown in the staff dashboard)

The free Gemini tier allows about 15 requests a minute and one chat message uses 2 to 3, so the runner pauses between
messages. A full run takes around 10 minutes. Tickets go to a throwaway file, never to your real tickets.csv.
Every run is also saved offline in evals/runs/ (timestamped .json and .txt, plus latest.txt).
Exit code is 0 only if every selected case passes.
"""
import argparse
import asyncio
import csv
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Use a throwaway ticket file. This must be set before pulse_agent is imported.
_tmp = tempfile.mkdtemp(prefix="pulse-evals-")
TICKETS = Path(_tmp) / "tickets.csv"
os.environ["PULSE_TICKETS_FILE"] = str(TICKETS)

PAUSE = float(os.getenv("EVAL_PAUSE", "13"))  # seconds between model calls (free-tier pacing)
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def tickets_now() -> list[dict]:
    if not TICKETS.exists():
        return []
    with TICKETS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check(expect: dict, reply: str, new_tickets: list[dict]) -> list[str]:
    """Returns a list of failure messages (empty = pass)."""
    fails, low = [], reply.lower()
    for s in expect.get("contains_all", []):
        if s.lower() not in low:
            fails.append(f"missing '{s}'")
    if expect.get("contains_any") and not any(s.lower() in low for s in expect["contains_any"]):
        fails.append(f"none of {expect['contains_any']}")
    for s in expect.get("not_contains", []):
        if s.lower() in low:
            fails.append(f"should not contain '{s}'")
    for rx in expect.get("regex", []):
        if not re.search(rx, reply, re.S):
            fails.append(f"regex not matched: {rx}")
    if expect.get("source") and "(source:" not in low:
        fails.append("no (Source: ...) given")
    if expect.get("devanagari") is True and not DEVANAGARI.search(reply):
        fails.append("reply is not in Devanagari script")
    if expect.get("devanagari") is False and DEVANAGARI.search(reply):
        fails.append("reply unexpectedly in Devanagari script")
    if expect.get("asks_question") and "?" not in reply:
        fails.append("did not ask a question")
    t = expect.get("ticket")
    if t == "none" and new_tickets:
        fails.append(f"unexpected ticket {new_tickets[0]['ticket_id']}")
    if t in ("any", "normal", "high"):
        if not new_tickets:
            fails.append("no ticket was created")
        elif t in ("normal", "high") and new_tickets[0].get("priority") != t:
            fails.append(f"ticket priority {new_tickets[0].get('priority')} (wanted {t})")
    for field in expect.get("ticket_fields", []):
        if not new_tickets or not (new_tickets[0].get(field) or "").strip():
            fails.append(f"ticket field '{field}' is empty")
    for s in expect.get("ticket_summary_not_contains", []):
        if new_tickets and s in (new_tickets[0].get("summary") or ""):
            fails.append(f"ticket summary leaks '{s}'")
    return fails


async def ask(runner, session_id: str, text: str) -> str:
    from google.genai import types

    for attempt in range(4):
        try:
            reply = ""
            async for event in runner.run_async(
                user_id="eval", session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part(text=text)]),
            ):
                if event.content and event.content.parts and event.is_final_response():
                    reply = "".join(p.text or "" for p in event.content.parts).strip()
            return reply
        except Exception as e:
            msg = str(e)
            if ("429" in msg or "RESOURCE_EXHAUSTED" in msg or "503" in msg or "UNAVAILABLE" in msg) and attempt < 3:
                wait = 25 * (attempt + 1)
                print(f"    (Gemini busy, waiting {wait}s)", flush=True)
                await asyncio.sleep(wait)
                continue
            raise
    return ""


RUNS_DIR = ROOT / "evals" / "runs"


def format_report(summary: dict) -> str:
    """A readable text report of one run."""
    lines = [
        "PULSE EVAL RUN",
        f"Date:     {summary['run_at']}   (took {summary['duration_s']}s)",
        f"Commit:   {summary.get('commit', 'unknown')}",
        f"Result:   {summary['passed']}/{summary['total']} passed",
        "Groups:   " + "   ".join(f"{t} {d['passed']}/{d['total']}" for t, d in sorted(summary["by_tag"].items())),
        "",
    ]
    for c in summary["cases"]:
        lines.append(f"{'PASS' if c['passed'] else 'FAIL'}  {c['id']}")
        lines.append(f"      asked: {c.get('question', '')}")
        if not c["passed"]:
            lines.append(f"      why:   {'; '.join(c['failures'])}")
        lines.append(f"      reply: {c['reply'].replace(chr(10), ' ')}")
        lines.append("")
    return chr(10).join(lines)


def save_run(summary: dict, label: str) -> Path:
    """Every run is saved offline in evals/runs/ (a timestamped .json and .txt, plus latest.txt)."""
    import subprocess

    try:
        summary["commit"] = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                                           text=True, timeout=10).stdout.strip() or "unknown"
    except Exception:
        summary["commit"] = "unknown"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    base = RUNS_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{label}"
    base.with_suffix(".json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    report = format_report(summary)
    base.with_suffix(".txt").write_text(report, encoding="utf-8")
    (RUNS_DIR / "latest.txt").write_text(report, encoding="utf-8")
    return base.with_suffix(".txt")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", help="comma-separated tags to run")
    ap.add_argument("--ids", help="comma-separated case ids to run")
    ap.add_argument("--quick", action="store_true", help="run the cases tagged 'quick'")
    ap.add_argument("--save", action="store_true", help="write evals/results.json")
    ap.add_argument("--out", help="write results to this path instead")
    ap.add_argument("--merge", action="store_true", help="with --save/--out: update only these cases inside the existing results file")
    a = ap.parse_args()

    data = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    if a.quick:
        cases = [c for c in cases if "quick" in c["tags"]]
    if a.tags:
        want = set(a.tags.split(","))
        cases = [c for c in cases if want & set(c["tags"])]
    if a.ids:
        want = set(a.ids.split(","))
        cases = [c for c in cases if c["id"] in want]
    if not cases:
        print("No cases selected.")
        return 2

    from google.adk.runners import InMemoryRunner

    from pulse_agent.agent import root_agent

    runner = InMemoryRunner(agent=root_agent, app_name="pulse_evals")
    started, results = time.time(), []
    print(f"Running {len(cases)} cases (about {int(len(cases) * PAUSE * 1.3 / 60) + 1} min)...\n", flush=True)
    for i, c in enumerate(cases, 1):
        before = len(tickets_now())
        sess = await runner.session_service.create_session(app_name="pulse_evals", user_id="eval")
        reply, err = "", ""
        try:
            for turn in c["turns"]:
                await asyncio.sleep(PAUSE)
                reply = await ask(runner, sess.id, turn)
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:120]}"
        new = tickets_now()[before:]
        fails = [f"error: {err}"] if err else check(c["expect"], reply, new)
        ok = not fails
        results.append({"id": c["id"], "tags": c["tags"], "passed": ok, "failures": fails,
                        "reply": reply[:300], "turns": c["turns"]})
        print(f"[{i:>2}/{len(cases)}] {'PASS' if ok else 'FAIL'}  {c['id']}" + ("" if ok else f"\n        -> {'; '.join(fails)}\n        reply: {reply[:160]!r}"), flush=True)

    passed = sum(r["passed"] for r in results)
    by_tag = {}
    for r in results:
        for t in r["tags"]:
            d = by_tag.setdefault(t, {"passed": 0, "total": 0})
            d["total"] += 1
            d["passed"] += int(r["passed"])
    summary = {
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "duration_s": int(time.time() - started),
        "passed": passed, "total": len(results), "by_tag": by_tag,
        "cases": [{k: v for k, v in r.items() if k != "turns"} | {"question": r["turns"][-1]} for r in results],
    }
    print(f"\n{passed}/{len(results)} passed in {summary['duration_s']}s  " + "  ".join(f"{t}: {d['passed']}/{d['total']}" for t, d in sorted(by_tag.items())))
    label = "-".join(x for x in [
        "quick" if a.quick else "",
        a.tags.replace(",", "+") if a.tags else "",
        ("ids-" + a.ids.replace(",", "+"))[:40] if a.ids else "",
    ] if x) or "full"
    saved = save_run(summary, label)
    print(f"Run saved offline: {saved}  (and .json)")
    out = Path(a.out) if a.out else (ROOT / "evals" / "results.json" if a.save else None)
    if out and a.merge and out.exists():
        old_run = json.loads(out.read_text(encoding="utf-8"))
        fresh = {c["id"]: c for c in summary["cases"]}
        merged = [fresh.pop(c["id"], c) for c in old_run["cases"]] + list(fresh.values())
        by_tag = {}
        for c in merged:
            for t in c["tags"]:
                d = by_tag.setdefault(t, {"passed": 0, "total": 0})
                d["total"] += 1
                d["passed"] += int(c["passed"])
        summary.update(cases=merged, passed=sum(c["passed"] for c in merged), total=len(merged), by_tag=by_tag,
                       duration_s=old_run.get("duration_s", 0) + summary["duration_s"])
    if out:
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved {out}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(asyncio.run(main()))
