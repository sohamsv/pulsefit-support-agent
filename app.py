"""PulseFit Gym Support: Streamlit page that talks to the same ADK agent (pulse_agent)."""
import asyncio
import hmac
import os
import time
import uuid

import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # laptop: GOOGLE_API_KEY from .env

st.set_page_config(page_title="PulseFit Gym Support", page_icon="💪")


def _secret(name: str):
    """Read a Streamlit secret, or None if secrets are not set up."""
    try:
        return st.secrets[name]
    except Exception:
        return None


# Deployed: GOOGLE_API_KEY comes from Streamlit secrets. Laptop: from .env (loaded above).
if _secret("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = _secret("GOOGLE_API_KEY")

GREETING = "Hey, I'm Pulse from PulseFit! How can I help you today?"

st.title("PulseFit Gym Support 💪")

# ---------- Passcode gate ----------
PASSCODE = _secret("APP_PASSCODE")
if not PASSCODE:
    st.error("APP_PASSCODE is not set in Streamlit secrets, so the chat stays locked.")
    st.stop()

if not st.session_state.get("unlocked"):
    entered = st.text_input("Enter the passcode to open the chat", type="password")
    if entered:
        if hmac.compare_digest(entered.encode(), str(PASSCODE).encode()):
            st.session_state.unlocked = True
            st.rerun()
        else:
            st.error("Wrong passcode. The chat stays locked.")
    st.stop()


# ---------- Agent (same ADK agent, called from the page) ----------
@st.cache_resource(show_spinner="Getting Pulse ready (first load builds the help-docs index)...")
def get_runner():
    from google.adk.runners import InMemoryRunner

    from pulse_agent.agent import root_agent  # builds the index at import if missing

    return InMemoryRunner(agent=root_agent, app_name="pulsefit_web")


async def ask_pulse(runner, session_id: str, text: str) -> str:
    from google.genai import types

    if not st.session_state.get("adk_session_created"):
        await runner.session_service.create_session(
            app_name="pulsefit_web", user_id="web", session_id=session_id
        )
        st.session_state.adk_session_created = True
    reply = ""
    async for event in runner.run_async(
        user_id="web",
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=text)]),
    ):
        if event.content and event.content.parts and event.is_final_response():
            reply = "".join(p.text or "" for p in event.content.parts).strip()
    return reply or "Sorry, I couldn't come up with a reply. Please try again."


runner = get_runner()

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Ask Pulse about memberships, classes, timings..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Pulse is typing..."):
            answer = None
            for attempt in range(3):  # retry temporary Google errors (503 busy)
                try:
                    answer = asyncio.run(ask_pulse(runner, st.session_state.session_id, prompt))
                    break
                except Exception as e:
                    msg = str(e)
                    if ("503" in msg or "UNAVAILABLE" in msg) and attempt < 2:
                        time.sleep(3)
                        continue
                    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                        answer = "I'm getting a lot of questions right now. Please wait a minute and try again."
                    else:
                        answer = "Sorry, something went wrong on my side. Please try again."
                    break
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

# ---------- Sidebar: open tickets (rendered last so new tickets show up straight away) ----------
from pulse_agent.tickets import list_open_tickets  # noqa: E402

with st.sidebar:
    st.header("Open tickets")
    tickets = list_open_tickets()
    if not tickets:
        st.caption("No open tickets yet.")
    for t in reversed(tickets):
        flag = "🔴 HIGH" if t["priority"] == "high" else "🟢 normal"
        st.markdown(f"**{t['ticket_id']}** · {flag}  \n{t['reason']}  \n_{t['time']}_")
        st.divider()
