"""Authentication endpoints."""

from fastapi import APIRouter

from app.dependencies import AuthServiceDep
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    token = auth_service.login(payload.email, payload.password)
    return TokenResponse(access_token=token)
