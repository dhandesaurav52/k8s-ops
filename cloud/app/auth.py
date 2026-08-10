import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from cloud.app.config import settings


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_session_token(username: str, role: str = "operator", expires_in_seconds: int = 86400) -> str:
    """Create a HMAC-SHA256 signed session token."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    header_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    msg = f"{header_b64}.{payload_b64}".encode("utf-8")

    sig = hmac.new(settings.SKYOPS_SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
    sig_b64 = b64url_encode(sig)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify an HMAC-SHA256 signed session token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, sig_b64 = parts
        msg = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(settings.SKYOPS_SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).digest()
        provided_sig = b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None  # Token expired

        return payload
    except Exception:
        return None


def verify_agent_token(token: str) -> bool:
    """Constant-time verification of SKYOPS_AGENT_TOKEN."""
    if not token or not settings.SKYOPS_AGENT_TOKEN:
        return False
    return hmac.compare_digest(token, settings.SKYOPS_AGENT_TOKEN)


def verify_admin_credentials(username: str, password: str) -> bool:
    """Constant-time verification of admin credentials."""
    user_ok = hmac.compare_digest(username, settings.SKYOPS_ADMIN_USERNAME)
    pass_ok = hmac.compare_digest(password, settings.SKYOPS_ADMIN_PASSWORD)
    return user_ok and pass_ok


def get_current_identity(request: Request) -> Dict[str, Any]:
    """
    FastAPI security dependency to authenticate requests via:
    1. Authorization Bearer header (Agent Token OR User Session Token)
    2. HttpOnly Cookie 'skyops_session'
    """
    auth_header = request.headers.get("Authorization", "")
    bearer_token = ""
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()

    cookie_token = request.cookies.get("skyops_session", "").strip()

    # 1. Check Agent Token (Bearer)
    if bearer_token and verify_agent_token(bearer_token):
        return {"type": "agent", "sub": "agent", "role": "agent"}

    # 2. Check User Session Token (Bearer or Cookie)
    token_to_check = bearer_token or cookie_token
    if token_to_check:
        user_payload = decode_session_token(token_to_check)
        if user_payload:
            return {
                "type": "user",
                "sub": user_payload.get("sub", "operator"),
                "role": user_payload.get("role", "operator"),
            }

    # 3. Reject if unauthenticated
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Missing or invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
