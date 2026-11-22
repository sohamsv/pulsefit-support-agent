"""API tests. Pulse is replaced by a fake, so no Gemini calls are made."""
import csv
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from api import agent_runner, db as dbmod
from api.main import create_app


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    tickets_csv = tmp_path / "tickets.csv"
    monkeypatch.setattr(dbmod, "TICKETS_CSV", tickets_csv)
    monkeypatch.setenv("STAFF_PASSCODE", "staff-pass")
    monkeypatch.setenv("API_SECRET", "test-secret")
    monkeypatch.setenv("CHAT_PER_IP_PER_MIN", "3")
    monkeypatch.setenv("CHAT_GLOBAL_PER_MIN", "4")
    monkeypatch.setenv("TRIAL_PER_IP_PER_HOUR", "2")
    calls = []

    async def fake_pulse(session_id, text):
        calls.append(text)
        if "hurt" in text:
            with open(tickets_csv, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if f.tell() == 0:
                    w.writerow(["ticket_id", "time", "message", "reason", "priority", "status"])
                w.writerow(["TKT-1001", "2026-11-22 10:00:00", text, "injury", "high", "open"])
            return {"reply": "Stop and get staff help. Ticket TKT-1001.", "ticket_ids": ["TKT-1001"]}
        if "loyalty" in text:
            return {"reply": "I don't have that information. Would you like me to connect you to a person?", "ticket_ids": []}
        return {"reply": "Hi from Pulse", "ticket_ids": []}

    app = create_app(db_path=tmp_path / "t.db", run_pulse=fake_pulse)
    client = TestClient(app)
    return client, calls, tmp_path


def staff_headers(client):
    r = client.post("/staff/login", json={"passcode": "staff-pass"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------------- chat ----------------
def test_chat_returns_reply_and_session(ctx):
    client, _, _ = ctx
    r = client.post("/chat", json={"message": "Hi"})
    assert r.status_code == 200 and r.json()["reply"] == "Hi from Pulse" and r.json()["session_id"]


def test_chat_validation(ctx):
    client, _, _ = ctx
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "x" * 501}).status_code == 422


def test_chat_ticket_flow_visible_to_staff(ctx):
    client, _, _ = ctx
    r = client.post("/chat", json={"message": "I hurt my back"})
    assert r.json()["ticket_ids"] == ["TKT-1001"]
    t = client.get("/tickets", headers=staff_headers(client)).json()["tickets"]
    assert t[0]["ticket_id"] == "TKT-1001" and t[0]["priority"] == "high" and t[0]["status"] == "open"


def test_chat_per_visitor_rate_limit(ctx):
    client, calls, _ = ctx
    codes = [client.post("/chat", json={"message": f"q{i}"}).status_code for i in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    assert len(calls) == 3  # blocked requests never reach the model
    r = client.post("/chat", json={"message": "again"})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1


def test_chat_global_rate_limit(ctx):
    client, calls, _ = ctx
    # many visitors, but the free Gemini budget is shared
    from api.main import create_app as _c  # noqa: F401
    for i in range(4):
        client.app.state.limiters[0].reset()  # reset per-visitor limit between requests
        assert client.post("/chat", json={"message": f"q{i}"}).status_code == 200
    client.app.state.limiters[0].reset()
    assert client.post("/chat", json={"message": "q5"}).status_code == 429
    assert len(calls) == 4


def test_chat_model_busy_and_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(dbmod, "TICKETS_CSV", tmp_path / "t.csv")
    monkeypatch.setenv("API_SECRET", "s")

    async def busy(sid, text):
        raise agent_runner.ModelBusy()

    async def down(sid, text):
        raise agent_runner.ModelUnavailable()

    assert TestClient(create_app(tmp_path / "a.db", busy)).post("/chat", json={"message": "hi"}).status_code == 429
    assert TestClient(create_app(tmp_path / "b.db", down)).post("/chat", json={"message": "hi"}).status_code == 503


def test_chat_logs_redact_digits_and_flag_docs_gaps(ctx):
    client, _, _ = ctx
    client.post("/chat", json={"message": "do you have a loyalty program? my phone 9876543210"})
    stats = client.get("/staff/stats", headers=staff_headers(client)).json()
    assert stats["total_chats"] == 1
    gap = stats["docs_gaps"][0]["question"]
    assert "9876543210" not in gap and "[digits]" in gap


# ---------------- staff ----------------
def test_staff_endpoints_need_login(ctx):
    client, _, _ = ctx
    for path in ("/tickets", "/staff/stats", "/staff/trials"):
        assert client.get(path).status_code == 401
    assert client.get("/tickets", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_staff_login_lockout(ctx):
    client, _, _ = ctx
    codes = [client.post("/staff/login", json={"passcode": "bad"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    # even the right passcode is refused while locked out
    assert client.post("/staff/login", json={"passcode": "staff-pass"}).status_code == 429


def test_update_ticket_status_and_notes(ctx):
    client, _, _ = ctx
    client.post("/chat", json={"message": "I hurt my back"})
    h = staff_headers(client)
    r = client.patch("/tickets/TKT-1001", json={"status": "in_progress", "notes": "Called member"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "in_progress" and r.json()["notes"] == "Called member"
    # a later re-sync from the CSV must not overwrite the staff's status
    assert client.get("/tickets", headers=h).json()["tickets"][0]["status"] == "in_progress"
    assert client.get("/tickets?status=open", headers=h).json()["tickets"] == []
    assert client.patch("/tickets/TKT-1001", json={"status": "bogus"}, headers=h).status_code == 422
    assert client.patch("/tickets/TKT-9999", json={"status": "resolved"}, headers=h).status_code == 404
    assert client.patch("/tickets/TKT-1001", json={}, headers=h).status_code == 422


# ---------------- members ----------------
def test_member_login_and_me(ctx):
    client, _, _ = ctx
    r = client.post("/member/login", json={"member_id": "pf1001", "phone_last4": "3840"})
    assert r.status_code == 200
    me = client.get("/member/me", headers={"Authorization": f"Bearer {r.json()['token']}"}).json()
    assert me["member_id"] == "PF1001" and me["status"] == "Expired" and me["action_needed"]
    assert "phone_last4" not in me


def test_member_login_failures_are_generic_and_never_leak(ctx):
    client, _, _ = ctx
    wrong_digits = client.post("/member/login", json={"member_id": "PF1001", "phone_last4": "0000"})
    wrong_id = client.post("/member/login", json={"member_id": "PF9999", "phone_last4": "3840"})
    assert wrong_digits.status_code == wrong_id.status_code == 401
    assert wrong_digits.json() == wrong_id.json()
    assert "Siddharth" not in wrong_digits.text and "Expired" not in wrong_digits.text


def test_member_login_lockout_after_5_wrong_tries(ctx):
    client, _, _ = ctx
    codes = [client.post("/member/login", json={"member_id": "PF1001", "phone_last4": f"000{i}"}).status_code for i in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    assert client.post("/member/login", json={"member_id": "PF1001", "phone_last4": "3840"}).status_code == 429


def test_member_token_cannot_open_staff_pages(ctx):
    client, _, _ = ctx
    tok = client.post("/member/login", json={"member_id": "PF1001", "phone_last4": "3840"}).json()["token"]
    assert client.get("/tickets", headers={"Authorization": f"Bearer {tok}"}).status_code == 401
    assert client.get("/member/me").status_code == 401


# ---------------- free trial ----------------
def test_trial_booking_validation_and_limit(ctx):
    client, _, _ = ctx
    good = {"name": "Asha Rao", "phone": "9876543210", "branch": "Panjim", "preferred_date": (date.today() + timedelta(days=2)).isoformat()}
    assert client.post("/trial", json=good).status_code == 200
    assert client.post("/trial", json={**good, "phone": "123"}).status_code == 422
    assert client.post("/trial", json={**good, "branch": "Mars"}).status_code == 422
    assert client.post("/trial", json={**good, "preferred_date": "2020-01-01"}).status_code == 422
    assert client.post("/trial", json=good).status_code == 200  # 2nd allowed
    assert client.post("/trial", json=good).status_code == 429  # 3rd within the hour blocked
    assert len(client.get("/staff/trials", headers=staff_headers(client)).json()["trials"]) == 2
