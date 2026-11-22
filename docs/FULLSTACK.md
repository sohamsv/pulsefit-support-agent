# PulseFit full-stack extension (branch `extend-fullstack`)

Pulse (the support agent) is one part of a small end-to-end product. All data is made up.

```
Browser: Next.js site (web/)  --HTTP/JSON-->  FastAPI (api/)  -->  Pulse ADK agent (pulse_agent/)
 pages: Home, Plans, Classes,                  /chat /tickets        |  RAG over help docs (Chroma)
 Free trial, Member portal,                    /member/* /trial      |  create_ticket, membership lookup
 Staff dashboard, chat widget                  SQLite (api/data/)    |  safety check before the model
```

## Run it locally (3 terminals, from the project root)
1. API:      `python -m uvicorn api.main:app --port 8001`
2. Website:  `cd web && npm install && npm run dev`  (http://localhost:3000)
3. (Optional) the original Streamlit app still works: `streamlit run app.py`

Needs `.env` with `GOOGLE_API_KEY`, `STAFF_PASSCODE`, `API_SECRET` (see `api/.env.example`).
The website reads `NEXT_PUBLIC_API_URL` (default `http://localhost:8001`, see `web/.env.example`).

## What each part does
| Part | What it does |
|---|---|
| Public site | Plans, classes, FAQ, free-trial form, Pulse chat widget on every page |
| Member portal | Log in with member ID + last 4 phone digits, see your own plan and status |
| Staff dashboard | Passcode login, tickets (high priority first), status + notes, stats, docs gaps, trial bookings |
| API | Chat, tickets, member login, trial bookings, rate limits |

## Rate limits (built around the free Gemini quota of about 15 requests a minute)
- Chat: 4 messages a minute per visitor and 5 a minute for everyone together, at most 2 running at once.
  Blocked requests never reach the model. The API answers 429 with a `Retry-After`; the chat widget shows a countdown.
- The widget also paces itself (3 seconds between messages) and a temporary Google 503 is retried automatically.
- Harm messages are caught by a code check before the model, so they use no quota.
- Logins: 5 wrong tries lock a member ID (per visitor) for 15 minutes, 12 wrong tries lock the visitor, and 5 wrong staff passcodes lock staff login.
- Free-trial bookings: 3 an hour per visitor.

## Tests
- `python -m pytest api/tests -q` (no Gemini calls)
- `cd web && npm run lint && npm run build`

## Keeping the live Streamlit app safe
Streamlit Cloud deploys `main`. Work on this branch never touches it. New code lives in `api/` and `web/`,
the API has its own `api/requirements.txt`, and the only change to shared code is one backward-compatible line
in `pulse_agent/tickets.py` (an optional `PULSE_TICKETS_FILE` setting). Merge only after a pull request check
that `streamlit run app.py` and `test_tricky.py` still pass.

## Practice-grade limits
Logins are simple (ID + 4 digits, one staff passcode) and state is in memory and SQLite. Fine for made-up data, not for real members.
