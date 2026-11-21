"""Membership status lookup. Returns details only when member ID AND phone last 4 match the SAME row."""
import csv
import hmac
from pathlib import Path

MEMBERSHIPS_PATH = Path(__file__).resolve().parent.parent / "data" / "memberships.csv"
NOT_FOUND = {"result": "not found"}


def get_membership_status(member_id: str, phone_last4: str) -> dict:
    """Look up ONE member's membership, only if the member ID and the last 4 digits of their
    phone number both match the same record. Ask the customer for BOTH before calling this.

    Args:
        member_id: the member ID, like PF1001.
        phone_last4: the last 4 digits of the phone number on the membership.

    Returns:
        The member's plan, start date, end date and status if both match, otherwise
        {"result": "not found"} with no details.
    """
    mid = str(member_id or "").strip().upper()
    last4 = str(phone_last4 or "").strip()
    if not mid or len(last4) != 4 or not last4.isdigit():
        return dict(NOT_FOUND)
    try:
        with MEMBERSHIPS_PATH.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return dict(NOT_FOUND)
    for row in rows:
        if row["member_id"].strip().upper() == mid and hmac.compare_digest(
            row["phone_last4"].strip().encode(), last4.encode()
        ):
            status = row["status"].strip()
            out = {
                "result": "found",
                "member_id": row["member_id"],
                "plan": row["plan"],
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "status": status,
            }
            if status.lower() == "expired":
                out["action_needed"] = "Membership has expired. Offer to raise a ticket for renewal help."
            return out
    return dict(NOT_FOUND)
