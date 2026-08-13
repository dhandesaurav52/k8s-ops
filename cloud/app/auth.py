import os
import base64
import hashlib
import hmac
import json
import time
import secrets
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, Request, Depends, status
from sqlalchemy.orm import Session

from cloud.app.config import settings
from cloud.app.database import get_db
from cloud.app.models.user import User, SystemSetting
from cloud.app.models.organization import Organization, Membership
from cloud.app.models.cluster import Cluster


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored PBKDF2 hash."""
    try:
        if not hashed or not hashed.startswith("pbkdf2:sha256:"):
            return False
        parts = hashed.split("$")
        if len(parts) != 3:
            return False
        _, salt_hex, key_hex = parts
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False


def generate_agent_token() -> str:
    """Generate a secure, random agent registration token."""
    return f"skyops_agent_tok_{secrets.token_urlsafe(24)}"


def create_session_token(username: str, role: str = "operator", expires_in_seconds: int = 86400) -> str:
    """Create an HMAC-SHA256 signed session token."""
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


def get_default_or_user_organization(db: Session, user: Optional[User] = None) -> Organization:
    """
    Get or create default organization for the user or system.
    Guarantees that an organization always exists.
    """
    if user:
        membership = db.query(Membership).filter(Membership.user_id == user.user_id).first()
        if membership:
            org = db.query(Organization).filter(Organization.org_id == membership.organization_id).first()
            if org:
                return org

    # Fallback/Default organization
    default_org = db.query(Organization).filter(Organization.slug == "default-org").first()
    if not default_org:
        default_org = Organization(
            org_id="org-default",
            name="Default Organization",
            slug="default-org",
        )
        db.add(default_org)
        db.commit()
        db.refresh(default_org)

    if user:
        # Create membership
        mem = db.query(Membership).filter(
            Membership.organization_id == default_org.org_id,
            Membership.user_id == user.user_id,
        ).first()
        if not mem:
            mem = Membership(
                organization_id=default_org.org_id,
                user_id=user.user_id,
                role="admin",
            )
            db.add(mem)
            db.commit()

    return default_org


def get_current_identity(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    FastAPI dependency to resolve the caller's identity (User vs Agent) and Organization context.
    """
    auth_header = request.headers.get("Authorization", "")
    bearer_token = ""
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:].strip()

    cookie_token = request.cookies.get("skyops_session", "").strip()
    token = bearer_token or cookie_token

    # 1. Check if token matches a Cluster Agent Token in DB
    if bearer_token:
        cluster = db.query(Cluster).filter(Cluster.agent_token == bearer_token).first()
        if cluster:
            return {
                "type": "agent",
                "cluster_id": cluster.cluster_id,
                "organization_id": cluster.organization_id,
                "role": "agent",
            }
        
        # Fallback to global SKYOPS_AGENT_TOKEN if defined
        if settings.SKYOPS_AGENT_TOKEN and hmac.compare_digest(bearer_token, settings.SKYOPS_AGENT_TOKEN):
            org = get_default_or_user_organization(db)
            return {
                "type": "agent",
                "cluster_id": "default-cluster",
                "organization_id": org.org_id,
                "role": "agent",
            }

    # 2. Check User Session Token
    if token:
        payload = decode_session_token(token)
        if payload:
            username = payload.get("sub", "admin")
            user = db.query(User).filter(User.username == username).first()
            org = get_default_or_user_organization(db, user)
            return {
                "type": "user",
                "username": username,
                "organization_id": org.org_id,
                "role": payload.get("role", "admin"),
            }

    # 3. Default fallback for local/unauthenticated UI requests
    org = get_default_or_user_organization(db)
    return {
        "type": "user",
        "username": "admin",
        "organization_id": org.org_id,
        "role": "admin",
    }
