"""SQLite storage: tickets, members, trial bookings and chat logs. All data is made up."""
import csv
import os
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "api" / "data" / "pulsefit.db"
MEMBERS_CSV = ROOT / "data" / "memberships.csv"
# Pulse's create_ticket tool writes this file. It lives next to the database so the two reset together
# (otherwise a reset CSV would reuse ticket IDs the database already has).
TICKETS_CSV = Path(os.getenv("PULSE_TICKETS_FILE") or ROOT / "api" / "data" / "tickets.csv")
os.environ["PULSE_TICKETS_FILE"] = str(TICKETS_CSV)
NO_ANSWER = "i don't have that information"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
  ticket_id TEXT PRIMARY KEY, time TEXT, message TEXT, reason TEXT,
  priority TEXT, status TEXT, notes TEXT DEFAULT '', updated_at TEXT);
CREATE TABLE IF NOT EXISTS members (
  member_id TEXT PRIMARY KEY, member_name TEXT, phone_last4 TEXT, plan TEXT,
  start_date TEXT, end_date TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS trials (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, branch TEXT,
  preferred_date TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS chat_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, session_id TEXT, question TEXT,
  reply TEXT, ticket_id TEXT, answered INTEGER);
"""


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def redact(text: str) -> str:
    """Never store phone digits or long numbers in chat logs."""
    return re.sub(r"\d{4,}", "[digits]", text or "")


class Database:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.executescript(SCHEMA)
        self.seed_members()

    def _conn(self):
        c = sqlite3.connect(self.path, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def query(self, sql, args=()):
        with self._lock, self._conn() as c:
            return [dict(r) for r in c.execute(sql, args).fetchall()]

    def execute(self, sql, args=()):
        with self._lock, self._conn() as c:
            cur = c.execute(sql, args)
            return cur.lastrowid

    # ---- members ----
    def seed_members(self, csv_path=MEMBERS_CSV):
        if self.query("SELECT 1 FROM members LIMIT 1") or not Path(csv_path).exists():
            return
        with open(csv_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                self.execute(
                    "INSERT OR IGNORE INTO members VALUES (?,?,?,?,?,?,?)",
                    (r["member_id"].strip().upper(), r["member_name"], r["phone_last4"].strip(),
                     r["plan"], r["start_date"], r["end_date"], r["status"]),
                )

    # ---- tickets ----
    def sync_tickets(self, csv_path=None):
        """Import tickets Pulse wrote to tickets.csv. Existing rows (and their status/notes) are kept."""
        path = Path(csv_path or TICKETS_CSV)
        if not path.exists():
            return
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            self.execute(
                "INSERT OR IGNORE INTO tickets (ticket_id,time,message,reason,priority,status,notes,updated_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (r["ticket_id"], r["time"], r["message"], r["reason"], r["priority"],
                 r.get("status") or "open", "", r["time"]),
            )

    def list_tickets(self, status=None, priority=None):
        self.sync_tickets()
        sql, args = "SELECT * FROM tickets WHERE 1=1", []
        if status:
            sql += " AND status=?"; args.append(status)
        if priority:
            sql += " AND priority=?"; args.append(priority)
        sql += " ORDER BY (priority='high') DESC, (status='resolved') ASC, time DESC"
        return self.query(sql, args)

    def update_ticket(self, ticket_id, status=None, notes=None):
        self.sync_tickets()
        if not self.query("SELECT 1 FROM tickets WHERE ticket_id=?", (ticket_id,)):
            return None
        if status is not None:
            self.execute("UPDATE tickets SET status=?, updated_at=? WHERE ticket_id=?", (status, now(), ticket_id))
        if notes is not None:
            self.execute("UPDATE tickets SET notes=?, updated_at=? WHERE ticket_id=?", (notes, now(), ticket_id))
        return self.query("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,))[0]

    # ---- chat logs ----
    def log_chat(self, session_id, question, reply, ticket_id=None):
        answered = 0 if NO_ANSWER in (reply or "").lower() else 1
        self.execute(
            "INSERT INTO chat_logs (time,session_id,question,reply,ticket_id,answered) VALUES (?,?,?,?,?,?)",
            (now(), session_id, redact(question)[:500], redact(reply)[:1500], ticket_id, answered),
        )

    # ---- stats ----
    def stats(self):
        self.sync_tickets()
        by = lambda col: {r[col]: r["n"] for r in self.query(f"SELECT {col}, COUNT(*) n FROM tickets GROUP BY {col}")}
        gaps = self.query(
            "SELECT question, COUNT(*) n FROM chat_logs WHERE answered=0 GROUP BY question ORDER BY n DESC, id DESC LIMIT 10"
        )
        top = self.query("SELECT question, COUNT(*) n FROM chat_logs GROUP BY question ORDER BY n DESC LIMIT 10")
        total = self.query("SELECT COUNT(*) n FROM chat_logs")[0]["n"]
        return {
            "tickets_by_status": by("status"),
            "tickets_by_priority": by("priority"),
            "tickets_by_reason": by("reason"),
            "total_chats": total,
            "docs_gaps": gaps,
            "top_questions": top,
        }
