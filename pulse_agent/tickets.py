"""Support tickets saved to tickets.csv. Ticket IDs are made by this code, never by the model."""
import csv
import os
import threading
from datetime import datetime
from pathlib import Path

# Default: tickets.csv in the project root. The API sets PULSE_TICKETS_FILE so the ticket file
# lives next to its database (api/data/), and the two are always reset together.
TICKETS_PATH = Path(os.getenv("PULSE_TICKETS_FILE") or Path(__file__).resolve().parent.parent / "tickets.csv")
FIELDS = ["ticket_id", "time", "message", "reason", "priority", "status"]
_lock = threading.Lock()


def _read_rows() -> list[dict]:
    if not TICKETS_PATH.exists():
        return []
    with TICKETS_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _next_id(rows: list[dict]) -> str:
    nums = []
    for r in rows:
        try:
            nums.append(int(r["ticket_id"].split("-")[1]))
        except (KeyError, IndexError, ValueError):
            pass
    return f"TKT-{(max(nums) + 1) if nums else 1001}"


def create_ticket(message: str, reason: str, priority: str = "normal") -> dict:
    """Raise a support ticket so a person from PulseFit follows up with the customer.

    Use this when someone got hurt (priority high), asks for a refund, reports a double
    charge or billing error, complains about a trainer or staff, is angry or upset, asks for
    a person, or when the help docs do not have the answer.

    Args:
        message: the customer's message, in their own words.
        reason: a short reason such as "injury", "refund request", "billing error",
            "complaint", "upset customer", "not in docs" or "asked for a person".
        priority: "high" for injuries, otherwise "normal".

    Returns:
        A dict with the ticket_id to share with the customer.
    """
    priority = (priority or "normal").strip().lower()
    if priority not in ("normal", "high"):
        priority = "normal"
    with _lock:
        rows = _read_rows()
        ticket_id = _next_id(rows)
        is_new = not TICKETS_PATH.exists()
        with TICKETS_PATH.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if is_new:
                w.writeheader()
            w.writerow({
                "ticket_id": ticket_id,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": message,
                "reason": reason,
                "priority": priority,
                "status": "open",
            })
    return {"ticket_id": ticket_id, "status": "open", "priority": priority}


def list_open_tickets() -> list[dict]:
    """For the Step 4 sidebar."""
    return [r for r in _read_rows() if r.get("status") == "open"]
