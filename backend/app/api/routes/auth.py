from datetime import timedelta

from fastapi import APIRouter, Depends, Header

from app.api.schemas.auth_schemas import AuthMeResponse, LoginRequest, LoginResponse
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.auth.security import (
    AuthTokenError,
    create_access_token,
    verify_access_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthenticationAppError(AppError):
    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(
            error_code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401,
            details={},
        )


def _validate_auth_settings(settings: Settings) -> tuple[str, str, str]:
    if (
        not settings.app_auth_username
        or not settings.app_auth_password_hash
        or not settings.app_auth_jwt_secret
    ):
        raise AuthenticationAppError("Authentication is not configured.")
    return (
        settings.app_auth_username,
        settings.app_auth_password_hash,
        settings.app_auth_jwt_secret,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    if not settings.app_auth_enabled:
        return LoginResponse(
            accessToken=create_access_token(
                username=request.username or "local",
                secret=settings.app_auth_jwt_secret or "local-dev-auth-disabled",
                expires_delta=timedelta(minutes=settings.app_auth_token_expire_minutes),
            ),
            expiresInSeconds=settings.app_auth_token_expire_minutes * 60,
            username=request.username or "local",
        )

    username, password_hash, jwt_secret = _validate_auth_settings(settings)
    if request.username != username or not verify_password(
        request.password,
        password_hash,
    ):
        raise AuthenticationAppError("Invalid username or password.")
    return LoginResponse(
        accessToken=create_access_token(
            username=username,
            secret=jwt_secret,
            expires_delta=timedelta(minutes=settings.app_auth_token_expire_minutes),
        ),
        expiresInSeconds=settings.app_auth_token_expire_minutes * 60,
        username=username,
    )


@router.get("/me", response_model=AuthMeResponse)
def me(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> AuthMeResponse:
    if not settings.app_auth_enabled:
        return AuthMeResponse(
            authEnabled=False,
            authenticated=True,
            username=None,
        )

    username, _password_hash, jwt_secret = _validate_auth_settings(settings)
    token = _bearer_token(authorization)
    if token is None:
        raise AuthenticationAppError("Authentication token is missing.")
    try:
        token_username = verify_access_token(
            token,
            secret=jwt_secret,
            expected_username=username,
        )
    except AuthTokenError as exc:
        raise AuthenticationAppError("Authentication token is invalid.") from exc
    return AuthMeResponse(
        authEnabled=True,
        authenticated=True,
        username=token_username,
    )


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix) :].strip()
    return token or None
