# PulseFit Gym: Pulse support agent + full-stack site

PulseFit is a made-up gym with branches in Goa. This project is an AI support agent called **Pulse**, and a small end-to-end product built around it: a public website, a member portal and a staff dashboard. Built for the MASAI AI Residency.

## Live links

| What | Link |
|---|---|
| Website (Vercel) | https://pulsefit-gym-ten.vercel.app |
| Staff dashboard | https://pulsefit-gym-ten.vercel.app/staff (passcode needed) |
| Member portal | https://pulsefit-gym-ten.vercel.app/member |
| Free trial form | https://pulsefit-gym-ten.vercel.app/trial |
| API (Render) | https://pulsefit-api-kuzt.onrender.com |
| API health check | https://pulsefit-api-kuzt.onrender.com/health |

The Render API is on the free plan and sleeps when idle. The first request can take 30 to 60 seconds. Open the health link first to wake it.

### Pulse support agent, chat only (Streamlit)

https://pulsefit-pulse.streamlit.app/

This is the original support agent from Steps 1 to 4, with just the chat and no website. It is deployed on Streamlit Cloud from the `main` branch.

## What Pulse does

- Answers questions from the gym's own help docs (RAG: Gemini embeddings + Chroma, top 3 chunks) and cites the source.
- Says "I don't have that information" instead of guessing, and offers a hand-off to a person.
- Hands off problems it can't solve (injury, double charge, complaints, "let me talk to a person") by creating a support ticket with a code-made ID (TKT-1001, ...). Injuries get high priority and the 108 emergency number.
- Looks up a membership only after the member ID and the last 4 phone digits match. It never lists members or shares other people's data.
- Refuses off-topic requests, prompt injection and free-extension tricks.
- Has a code-level safety check before the model: threats of harm and self-harm get the emergency numbers (112 / 108) and no ticket. Gym slang like "murder this deadlift" is allowed.

Built with Google ADK (Python) and Gemini `gemini-3.5-flash-lite`.

## The pieces

```
pulse_agent/   the agent: tools, RAG, safety filter, tickets, membership lookup
app.py         Streamlit chat app (the original deliverable, deployed from main)
api/           FastAPI backend: /chat, tickets, members, trial bookings, staff stats
web/           Next.js website, member portal, staff dashboard, chat widget
evals/         46 test conversations, runner, saved run history
tests/         fast tests that need no Gemini calls
docs/          FULLSTACK.md: architecture, rate limits, deploying
```

- **Website:** home, plans, classes, free-trial form, floating Pulse chat widget.
- **Member portal:** log in with member ID and last 4 phone digits to see plan status.
- **Staff dashboard:** tickets (status and notes), chat stats, questions the docs couldn't answer, trial bookings, and an **Agent quality** panel showing every eval check.

## Designed around the free Gemini quota

The free tier allows about 15 requests a minute, and one chat message uses 2 to 3. So `/chat` is limited per visitor (4 a minute) and globally (5 a minute), with at most 2 chats at once. Wrong staff or member logins lock out for 15 minutes after 5 tries. Trial bookings are limited to 3 an hour per visitor.

## Run it locally

```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# put GOOGLE_API_KEY in .env, then build the index once:
python build_index.py

adk web                     # chat in the ADK UI
streamlit run app.py        # Streamlit chat app

pip install -r api/requirements.txt
python -m uvicorn api.main:app --port 8001     # API (also set STAFF_PASSCODE, API_SECRET in .env)

cd web && npm install && npm run dev           # website on http://localhost:3000
```

## Tests and evals

```
python -m pytest tests api/tests -q      # fast, no Gemini calls
python evals/run_evals.py --quick        # about 12 key cases, 3 to 4 minutes
python evals/run_evals.py --save         # full run, updates the dashboard panel
```

Every eval run is saved in `evals/runs/` (timestamped `.json` and readable `.txt`). Core behaviors: 33/33 passing at the last full run.

## Deploying

- Website: Vercel CLI from `web/` (`npx vercel deploy --prod`), with `NEXT_PUBLIC_API_URL` pointing to the Render API.
- API: Render web service (see `render.yaml`), redeployed with the Render CLI. Env vars: `GOOGLE_API_KEY`, `STAFF_PASSCODE`, `API_SECRET`, `TRUST_PROXY`.
- Streamlit: deploys from `main` using the root `requirements.txt`.

Details are in [docs/FULLSTACK.md](docs/FULLSTACK.md).

## Ideas for next

- Richer tickets: short summary, member mood and a suggested next step.
- Clarifying questions for vague messages ("cancel my membership" without a plan).
- Replies in Hindi, Marathi and Hinglish.
