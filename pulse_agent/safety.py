"""Hard safety check that runs BEFORE the model. Messages about harming people or self-harm get a fixed,
serious reply and never reach the model, so they can't create tickets or get a cheerful answer."""
import re
from typing import Optional

from google.adk.models import LlmResponse
from google.genai import types

VIOLENCE_REPLY = (
    "I can't help with anything that could hurt someone. If anyone is in danger right now, "
    "please call 112 for emergency services, or 108 for a medical emergency."
)
SELF_HARM_REPLY = (
    "I'm really concerned about what you just shared, and I'm glad you said it. You don't have to "
    "face this alone. If you're in danger right now, please call 112 for emergency services, or "
    "reach out to a trusted person or a mental health helpline right away."
)

_VERBS = r"(kill|murder|stab|shoot|strangle|poison|hurt|beat up|attack|assault)"
SELF_HARM = re.compile(
    r"\b(kill myself|end my life|end it all|suicide|suicidal|want to die|hurt myself|harm myself|self[- ]?harm)\b"
)
VIOLENCE = [
    re.compile(r"\bmurder(s|ed|ing|er)?\b"),
    re.compile(r"\b(want|wanna|going|gonna|plan|planning|help|need|ready|about|let'?s|should|will|i'll)\b.{0,25}\b" + _VERBS + r"\b(?! me\b)"),
    re.compile(r"\b(kill|stab|shoot|strangle|poison)\s+(him|her|them|someone|somebody|people|a person|my \w+|you|the \w+)\b"),
]


# Gym slang like "murder this deadlift" or "kill that workout" is not a threat. Only these clear gym words are
# ignored, so "murder this guy" is still caught.
GYM_SLANG = re.compile(
    r"\b(kill|murder|destroy|crush|smash)(s|ed|ing)?\s+(this|that|these|those|my|the|today'?s)\s+"
    r"(workout|session|set|sets|deadlifts?|squats?|lifts?|legs?|leg day|chest|back|cardio|class|run|gym|bench|pr)\b"
)


def check(text: str) -> Optional[str]:
    t = (text or "").lower().replace("’", "'")
    t = GYM_SLANG.sub(" ", t)
    if SELF_HARM.search(t):
        return SELF_HARM_REPLY
    if any(p.search(t) for p in VIOLENCE):
        return VIOLENCE_REPLY
    return None


def safety_callback(callback_context, llm_request) -> Optional[LlmResponse]:
    """ADK before_model_callback: only inspects the customer's latest typed message."""
    contents = llm_request.contents or []
    if not contents or contents[-1].role != "user":
        return None
    text = " ".join(p.text for p in (contents[-1].parts or []) if getattr(p, "text", None))
    reply = check(text)
    if reply is None:
        return None
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=reply)]))
