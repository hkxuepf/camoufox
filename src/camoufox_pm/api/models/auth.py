"""Auth API models."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials for ``POST /auth/login``."""

    username: str = Field(..., min_length=1, description="Account name")
    password: str = Field(..., min_length=1, description="Account password")


class RegisterRequest(BaseModel):
    """Credentials for ``POST /auth/register``."""

    username: str = Field(..., min_length=2, max_length=32, description="Account name")
    password: str = Field(..., min_length=6, max_length=128, description="Account password")


class AuthSessionResponse(BaseModel):
    """The caller's authentication state; also the login response."""

    user_auth_enabled: bool = Field(
        ..., description="Whether any user account exists, i.e. whether login is required"
    )
    authenticated: bool = Field(..., description="Whether this request carries a valid session")
    token: str | None = Field(None, description="Active session token")
    username: str | None = Field(None, description="The logged-in user, when authenticated")
    role: str = Field("user", description="Account role: admin or user")
    plan_id: str = Field("free", description="Subscription plan ID")
    max_profiles: int = Field(10, description="Profile quota limit")
    used_profiles: int = Field(0, description="Profiles currently created")
    max_concurrent: int = Field(2, description="Max concurrent browsers")
    expires_at: str | None = Field(None, description="Expiration date ISO")
    status: str = Field("active", description="Account status")

