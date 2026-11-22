"""PulseFit API: chat (Pulse agent), tickets (staff), member login, free-trial bookings.

Run:  uvicorn api.main:app --port 8001
"""
import asyncio
import os
import re
import secrets
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import agent_runner
from .db import Database
from .ratelimit import FailureLockout, SlidingWindow
from .security import make_token, read_token, same

load_dotenv()

# The deployed PulseFit website. Always allowed to call this API, in addition to CORS_ORIGINS.
PRODUCTION_ORIGINS = ["https://pulsefit-gym-ten.vercel.app"]
BRANCHES = ["Panjim", "Margao", "Mapusa"]
STATUSES = ["open", "in_progress", "resolved"]
SESSION_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
BUSY_MSG = "Pulse is getting a lot of questions right now. Please wait a few seconds and try again."


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: Optional[str] = None


class StaffLoginIn(BaseModel):
    passcode: str = Field(min_length=1, max_length=100)


class MemberLoginIn(BaseModel):
    member_id: str = Field(min_length=1, max_length=20)
    phone_last4: str = Field(min_length=1, max_length=10)


class TicketPatch(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class TrialIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    phone: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")
    branch: str
    preferred_date: date


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def create_app(db_path=None, run_pulse=None) -> FastAPI:
    """App factory. `run_pulse` can be replaced in tests so no real Gemini calls are made."""
    @asynccontextmanager
    async def lifespan(_app):
        # Real Pulse only (not in tests): load the agent and build the index in the background so
        # /health answers at once and the first chat does not pay for the index build.
        if run_pulse is None and os.getenv("WARM_PULSE", "1") == "1":
            threading.Thread(target=agent_runner.warm, daemon=True).start()
        yield

    app = FastAPI(title="PulseFit API", version="1.0", lifespan=lifespan)
    db = Database(db_path) if db_path else Database()
    ask_pulse = run_pulse or agent_runner.run_pulse

    # ---- rate limits (free Gemini tier is ~15 requests/minute; one chat uses 2 to 3 model calls) ----
    chat_ip = SlidingWindow(_int("CHAT_PER_IP_PER_MIN", 4), 60)
    chat_global = SlidingWindow(_int("CHAT_GLOBAL_PER_MIN", 5), 60)
    chat_slots = asyncio.Semaphore(_int("CHAT_CONCURRENCY", 2))
    trial_ip = SlidingWindow(_int("TRIAL_PER_IP_PER_HOUR", 3), 3600)
    staff_fail = FailureLockout(5, 900, 900)
    member_fail = FailureLockout(5, 900, 900)  # per IP + member ID
    member_ip_fail = FailureLockout(12, 900, 900)  # per IP, stops walking through many IDs
    app.state.limiters = [chat_ip, chat_global, trial_ip]
    app.state.db = db

    secret = os.getenv("API_SECRET") or secrets.token_hex(32)
    staff_pass = os.getenv("STAFF_PASSCODE", "")

    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    origins += [o for o in PRODUCTION_ORIGINS if o not in origins]  # the deployed website (exact URL, no wildcard)
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    def ip_of(request: Request) -> str:
        fwd = request.headers.get("x-forwarded-for")
        if fwd and os.getenv("TRUST_PROXY") == "1":
            return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def too_many(retry_after: int, msg: str = BUSY_MSG):
        return JSONResponse({"detail": msg, "retry_after": retry_after}, status_code=429,
                            headers={"Retry-After": str(retry_after)})

    def bearer(authorization: Optional[str]) -> Optional[str]:
        if authorization and authorization.lower().startswith("bearer "):
            return read_token(secret, authorization[7:].strip())
        return None

    def staff_only(authorization: Optional[str] = Header(default=None)):
        if bearer(authorization) != "staff":
            raise HTTPException(401, "Staff login required.")

    # ---------------------------------------------------------------- health
    @app.get("/health")
    def health():
        return {"ok": True}

    # ---------------------------------------------------------------- chat
    @app.post("/chat")
    async def chat(body: ChatIn, request: Request):
        msg = body.message.strip()
        if not msg:
            raise HTTPException(422, "Message is empty.")
        ok, wait = chat_ip.hit(ip_of(request))
        if not ok:
            return too_many(wait, "You're sending messages quickly. Please wait a few seconds.")
        ok, wait = chat_global.hit("all")
        if not ok:
            return too_many(wait)
        sid = body.session_id if body.session_id and SESSION_RE.match(body.session_id) else str(uuid.uuid4())
        async with chat_slots:
            try:
                out = await ask_pulse(sid, msg)
            except agent_runner.ModelBusy:
                return too_many(30)
            except agent_runner.ModelUnavailable:
                return JSONResponse({"detail": "Pulse is temporarily unavailable. Please try again shortly."}, status_code=503)
        tid = out["ticket_ids"][0] if out.get("ticket_ids") else None
        db.sync_tickets()
        db.log_chat(sid, msg, out["reply"], tid)
        return {"reply": out["reply"], "session_id": sid, "ticket_ids": out.get("ticket_ids", [])}

    # ---------------------------------------------------------------- staff
    @app.post("/staff/login")
    def staff_login(body: StaffLoginIn, request: Request):
        ip = ip_of(request)
        wait = staff_fail.blocked_for(ip)
        if wait:
            return too_many(wait, "Too many wrong passcodes. Try again later.")
        if not staff_pass:
            raise HTTPException(503, "Staff login is not configured.")
        if not same(body.passcode, staff_pass):
            staff_fail.fail(ip)
            raise HTTPException(401, "Wrong passcode.")
        staff_fail.success(ip)
        return {"token": make_token(secret, "staff")}

    @app.get("/tickets", dependencies=[Depends(staff_only)])
    def tickets(status: Optional[str] = None, priority: Optional[str] = None):
        if status and status not in STATUSES:
            raise HTTPException(422, "Bad status.")
        if priority and priority not in ("normal", "high"):
            raise HTTPException(422, "Bad priority.")
        return {"tickets": db.list_tickets(status, priority)}

    @app.patch("/tickets/{ticket_id}", dependencies=[Depends(staff_only)])
    def patch_ticket(ticket_id: str, body: TicketPatch):
        if body.status is not None and body.status not in STATUSES:
            raise HTTPException(422, "Bad status.")
        if body.status is None and body.notes is None:
            raise HTTPException(422, "Nothing to update.")
        row = db.update_ticket(ticket_id, body.status, body.notes)
        if not row:
            raise HTTPException(404, "Ticket not found.")
        return row

    @app.get("/staff/stats", dependencies=[Depends(staff_only)])
    def staff_stats():
        return db.stats()

    @app.get("/staff/trials", dependencies=[Depends(staff_only)])
    def staff_trials():
        return {"trials": db.query("SELECT * FROM trials ORDER BY id DESC LIMIT 100")}

    # ---------------------------------------------------------------- members
    @app.post("/member/login")
    def member_login(body: MemberLoginIn, request: Request):
        ip, mid, last4 = ip_of(request), body.member_id.strip().upper(), body.phone_last4.strip()
        keys = [f"{ip}|{mid}", ip]
        wait = max(member_fail.blocked_for(keys[0]), member_ip_fail.blocked_for(ip))
        if wait:
            return too_many(wait, "Too many tries. Please wait and try again later.")
        rows = db.query("SELECT * FROM members WHERE member_id=?", (mid,))
        row = rows[0] if rows else None
        # same generic answer whether the ID or the digits were wrong
        if not row or len(last4) != 4 or not same(row["phone_last4"], last4):
            member_fail.fail(keys[0])
            member_ip_fail.fail(ip)
            raise HTTPException(401, "We couldn't find a membership with those details.")
        member_fail.success(keys[0])
        return {"token": make_token(secret, f"member:{mid}", ttl=2 * 3600)}

    @app.get("/member/me")
    def member_me(authorization: Optional[str] = Header(default=None)):
        sub = bearer(authorization)
        if not sub or not sub.startswith("member:"):
            raise HTTPException(401, "Please log in.")
        rows = db.query("SELECT * FROM members WHERE member_id=?", (sub.split(":", 1)[1],))
        if not rows:
            raise HTTPException(401, "Please log in.")
        r = rows[0]
        r.pop("phone_last4", None)
        action = "Your membership has expired. Ask Pulse for renewal help." if r["status"] == "Expired" else None
        return {**r, "action_needed": action}

    # ---------------------------------------------------------------- free trial
    @app.get("/branches")
    def branches():
        return {"branches": BRANCHES}

    @app.post("/trial")
    def trial(body: TrialIn, request: Request):
        if body.branch not in BRANCHES:
            raise HTTPException(422, "Pick one of our branches.")
        if body.preferred_date < date.today():
            raise HTTPException(422, "Pick a date from today onwards.")
        ok, wait = trial_ip.hit(ip_of(request))  # only real bookings count toward the limit
        if not ok:
            return too_many(wait, "Too many booking requests. Please try again later.")
        tid = db.execute(
            "INSERT INTO trials (name,phone,branch,preferred_date,created_at) VALUES (?,?,?,?,datetime('now','localtime'))",
            (body.name.strip(), body.phone, body.branch, body.preferred_date.isoformat()),
        )
        return {"ok": True, "booking_id": tid, "message": "Your free 1-day pass request is in. Bring a photo ID."}

    return app


app = create_app()
