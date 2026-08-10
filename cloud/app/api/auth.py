from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from cloud.app.auth import (
    create_session_token,
    get_current_identity,
    verify_admin_credentials,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    status: str
    user: dict
    token: str


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(request_data: LoginRequest, response: Response):
    """Authenticate user with username and password and issue session token & cookie."""
    if not verify_admin_credentials(request_data.username, request_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_session_token(request_data.username)

    # Set HttpOnly, SameSite=lax session cookie
    response.set_cookie(
        key="skyops_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set true if HTTPS in production
        path="/",
        max_age=86400,
    )

    return LoginResponse(
        status="ok",
        user={"username": request_data.username, "role": "operator"},
        token=token,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response):
    """Clear session cookie."""
    response.delete_cookie(
        key="skyops_session",
        path="/",
        samesite="lax",
    )
    return {"status": "logged_out"}


@router.get("/me", status_code=status.HTTP_200_OK)
def get_me(identity: dict = Depends(get_current_identity)):
    """Retrieve current identity details."""
    return {"authenticated": True, "identity": identity}
