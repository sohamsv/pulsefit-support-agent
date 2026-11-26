"""Runs the existing Pulse ADK agent for the API. Pulse's own code is not changed."""
import asyncio

_runner = None
_known_sessions: set[str] = set()


class ModelBusy(Exception):
    """Gemini free-tier quota used up (429)."""


class ModelUnavailable(Exception):
    """Gemini temporarily unavailable (503) or another upstream failure."""


def _get_runner():
    global _runner
    if _runner is None:
        from google.adk.runners import InMemoryRunner

        from pulse_agent.agent import root_agent  # builds the help-docs index at import if missing

        _runner = InMemoryRunner(agent=root_agent, app_name="pulsefit_api")
    return _runner


async def _once(session_id: str, text: str) -> dict:
    from google.genai import types

    runner = _get_runner()
    if session_id not in _known_sessions:
        await runner.session_service.create_session(app_name="pulsefit_api", user_id="web", session_id=session_id)
        _known_sessions.add(session_id)
    reply, ticket_ids = "", []
    async for event in runner.run_async(
        user_id="web", session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=text)]),
    ):
        try:
            for fr in event.get_function_responses() or []:
                if fr.name == "create_ticket" and isinstance(fr.response, dict) and fr.response.get("ticket_id"):
                    ticket_ids.append(fr.response["ticket_id"])
        except Exception:
            pass
        if event.content and event.content.parts and event.is_final_response():
            reply = "".join(p.text or "" for p in event.content.parts).strip()
    return {"reply": reply or "Sorry, I couldn't come up with a reply. Please try again.", "ticket_ids": ticket_ids}


async def run_pulse(session_id: str, text: str) -> dict:
    """Ask Pulse. Retries a temporary Google 503 twice; turns 429 into ModelBusy."""
    for attempt in range(3):
        try:
            return await _once(session_id, text)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                raise ModelBusy() from e
            if ("503" in msg or "UNAVAILABLE" in msg) and attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise ModelUnavailable() from e
    raise ModelUnavailable()


def warm():
    """Load Pulse (and build the help-docs index if missing) ahead of the first chat. Never raises."""
    try:
        _get_runner()
    except Exception as e:  # the first real chat will surface the problem
        print(f"[warm-up] Pulse could not be loaded yet: {type(e).__name__}", flush=True)
