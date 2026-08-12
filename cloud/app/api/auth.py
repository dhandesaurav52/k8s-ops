from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from cloud.app.auth import (
    create_session_token,
    decode_session_token,
    get_current_identity,
    hash_password,
    is_initial_setup_completed,
    verify_admin_credentials,
    verify_initial_password,
    verify_password,
)
from cloud.app.database import get_db
from cloud.app.models.user import User, SystemSetting

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class InitialPasswordRequest(BaseModel):
    initial_password: str = Field(..., description="The initial administrator password retrieved from Kubernetes Secret")


class SetupAdminRequest(BaseModel):
    initial_password: str = Field(..., description="The initial administrator password")
    username: str = Field(..., min_length=3, max_length=150, description="Desired administrator username")
    email: Optional[str] = Field(None, max_length=255, description="Administrator email address")
    password: str = Field(..., min_length=6, description="New administrator password")


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Account password")


class LoginResponse(BaseModel):
    status: str
    user: dict
    token: str


@router.get("/status", status_code=status.HTTP_200_OK)
def get_auth_status(request: Request, db: Session = Depends(get_db)):
    """
    Public endpoint returning installation setup status and current session state.
    Used by Web UI to decide between Initial Setup screen, Login screen, and Dashboard.
    """
    setup_done = is_initial_setup_completed(db)

    # Check caller session if any
    auth_header = request.headers.get("Authorization", "")
    bearer_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    cookie_token = request.cookies.get("skyops_session", "").strip()
    token_to_check = bearer_token or cookie_token

    authenticated = False
    current_user = None

    if token_to_check:
        payload = decode_session_token(token_to_check)
        if payload:
            authenticated = True
            current_user = {
                "username": payload.get("sub", "operator"),
                "role": payload.get("role", "admin"),
            }

    return {
        "is_setup_completed": setup_done,
        "authenticated": authenticated,
        "user": current_user,
    }


@router.post("/verify-initial-password", status_code=status.HTTP_200_OK)
def verify_initial_admin_password(req: InitialPasswordRequest, db: Session = Depends(get_db)):
    """Verify initial administrator password during first-run setup."""
    if is_initial_setup_completed(db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial setup has already been completed. The initial administrator password is disabled.",
        )

    if not verify_initial_password(req.initial_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initial administrator password.",
        )

    return {"status": "ok", "message": "Initial password verified. Proceed to create administrator account."}


@router.post("/setup-admin", status_code=status.HTTP_201_CREATED)
def setup_administrator(req: SetupAdminRequest, db: Session = Depends(get_db)):
    """Create administrator account and complete initial setup."""
    if is_initial_setup_completed(db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial setup has already been completed.",
        )

    # Re-verify initial administrator password
    if not verify_initial_password(req.initial_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid initial administrator password.",
        )

    username_clean = req.username.strip().lower()

    # Check if username exists
    existing_user = db.query(User).filter(User.username == username_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{req.username}' is already taken.",
        )

    # Create new administrator user
    hashed = hash_password(req.password)
    admin_user = User(
        username=username_clean,
        email=req.email.strip().lower() if req.email else None,
        password_hash=hashed,
        role="admin",
    )
    db.add(admin_user)

    # Record setup completion
    setting = db.query(SystemSetting).filter(SystemSetting.key == "is_setup_completed").first()
    if not setting:
        setting = SystemSetting(key="is_setup_completed", value="true")
        db.add(setting)
    else:
        setting.value = "true"

    db.commit()

    return {
        "status": "ok",
        "message": "Administrator account created successfully. The initial password has been invalidated. Please log in.",
    }


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(request_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate administrator with username/email and password."""
    if not is_initial_setup_completed(db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Initial setup has not been completed yet. Please complete setup first.",
        )

    login_identifier = request_data.username.strip().lower()

    # Look up user in database by username or email
    user = (
        db.query(User)
        .filter((User.username == login_identifier) | (User.email == login_identifier))
        .first()
    )

    is_valid = False
    user_name = login_identifier
    user_role = "admin"
    user_email = None

    if user:
        if verify_password(request_data.password, user.password_hash):
            is_valid = True
            user_name = user.username
            user_role = user.role
            user_email = user.email
    else:
        # Fallback check for legacy default admin if DB has no user record
        if db.query(User).count() == 0 and verify_admin_credentials(request_data.username, request_data.password):
            is_valid = True
            user_name = request_data.username

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    token = create_session_token(username=user_name, role=user_role)

    # Set HttpOnly, SameSite=lax session cookie
    response.set_cookie(
        key="skyops_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
        max_age=86400,
    )

    return LoginResponse(
        status="ok",
        user={"username": user_name, "email": user_email, "role": user_role},
        token=token,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response):
    """Clear session cookie and log out."""
    response.delete_cookie(
        key="skyops_session",
        path="/",
        samesite="lax",
    )
    return {"status": "logged_out"}


@router.get("/me", status_code=status.HTTP_200_OK)
def get_me(identity: dict = Depends(get_current_identity)):
    """Retrieve current authenticated identity details."""
    return {"authenticated": True, "identity": identity}
