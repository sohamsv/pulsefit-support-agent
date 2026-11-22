"""Tiny signed-token helper (stdlib only) for the staff and member sessions. Practice-grade, not production auth."""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(secret: str, sub: str, ttl: int = 8 * 3600) -> str:
    body = _b64(json.dumps({"sub": sub, "exp": int(time.time()) + ttl}).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(secret: str, token: str) -> Optional[str]:
    """Returns the subject if the token is valid and not expired, else None."""
    try:
        body, sig = token.split(".", 1)
        good = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        data = json.loads(_unb64(body))
        return data["sub"] if data["exp"] > time.time() else None
    except Exception:
        return None


def same(a: str, b: str) -> bool:
    return hmac.compare_digest(str(a).encode(), str(b).encode())
