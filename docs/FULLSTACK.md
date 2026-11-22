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

## Deploying (Vercel for the website, Render for the API, both from the CLI)
Nothing here touches `main`, and the Streamlit app keeps deploying from `main`.

Live URLs (practice data only):
- Website (Vercel): https://pulsefit-gym-ten.vercel.app
- API (Render): https://pulsefit-api-kuzt.onrender.com (free plan, deploys the `extend-fullstack` branch)

### API on Render
Render builds from GitHub, so push the branch first. `render.yaml` documents the setup.
1. Log in once: `render login`, approve the code in the browser, then `render workspace set <workspace-id>`.
2. Create the service (first time only). Secrets come from your local `.env`, never from the repo:
   `render services create --name pulsefit-api --type web_service --runtime python --plan free --repo <github-url> --branch extend-fullstack --build-command "pip install -r api/requirements.txt" --start-command "python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT" --health-check-path /health --auto-deploy=false --env-var PYTHON_VERSION=3.13.5 --env-var TRUST_PROXY=1 --env-var GOOGLE_API_KEY=... --env-var STAFF_PASSCODE=... --env-var API_SECRET=<random>`
3. Redeploy after pushing changes: `render deploys create <service-id> --wait`. Logs: `render logs -r <service-id>`.
4. Check `GET <api-url>/health`, then one real `POST /chat`.

The Render CLI cannot change environment variables on an existing service. Change them in the Render dashboard, or
(as done for the website's address) put the value in code. The website's exact URL is in `PRODUCTION_ORIGINS` in `api/main.py`.

### Website on Vercel
From `web/`:
1. `npx vercel link --yes --project <name>`
2. Set the API address (baked in at build time): `printf '<api-url>' | npx vercel env add NEXT_PUBLIC_API_URL production`
3. `npx vercel deploy --prod --yes`. Redeploy whenever the API URL changes.

### Connecting the two
- The website calls the API at `NEXT_PUBLIC_API_URL`.
- The API only accepts browser calls from `CORS_ORIGINS` plus `PRODUCTION_ORIGINS`. A new website address needs a redeploy of the API.
- `TRUST_PROXY=1` on Render so the rate limits see each visitor's real IP.

### Free-tier caveats
- The API sleeps after 15 minutes without traffic, and the first request afterwards takes about a minute. Open the site a few minutes before a demo.
- The free disk is ephemeral: SQLite data, tickets and trial bookings reset on every restart or redeploy.
- The free instance has 512 MB of RAM. If the API ever runs out of memory, move the Render plan up.
- The Gemini free tier allows about 15 requests a minute, which is why chat is rate limited (see above).
- Render CLI login tokens expire after 7 days (`render login` again).
- Keep secrets in the host's settings. Rotate any key that has been pasted into a chat or document.

## Testing Pulse (evals)
Two kinds of checks, both from the project root:

| What | Command | Needs Gemini? |
|---|---|---|
| Fast code checks (safety filter) | `python -m pytest tests -q` | No |
| API tests (logins, tickets, rate limits, CORS) | `python -m pytest api/tests -q` | No |
| Pulse evals (about 46 cases) | `python evals/run_evals.py --quick` (12 cases), `--tags core`, `--ids a,b`, or `--save` for a full run | Yes, uses the free quota |

- Cases live in `evals/cases.json`: a message (or a short conversation) plus what the reply must and must not contain, whether a ticket is raised and its priority.
- Groups: `core` (existing behaviour), `tickets2`, `clarify`, `lang` (checks for features still being built), and `quick`.
- The runner pauses between messages to stay under the free Gemini limit (about 15 requests a minute), so a full run takes about 10 minutes. Tickets go to a throwaway file.
- `--save` writes `evals/results.json`. The staff dashboard's **Agent quality** panel shows those saved results. It never runs the evals live, so it costs no quota. To refresh the panel: run the evals with `--save`, commit `evals/results.json`, and redeploy the API.
