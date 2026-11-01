from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response, status

from chitbook_api.core.config import get_settings
from chitbook_api.core.deps import CurrentUser, SessionDep
from chitbook_api.core.errors import AUTHED, AppError, ErrorCode, errors
from chitbook_api.core.rate_limit import auth_rate_limit
from chitbook_api.modules.auth import repository, service
from chitbook_api.modules.auth.models import AuthEvent
from chitbook_api.modules.auth.schemas import (
    ClientType,
    LoginRequest,
    RefreshRequest,
    SessionOut,
    TokenResponse,
)
from chitbook_api.modules.users import service as users_service
from chitbook_api.modules.users.schemas import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "chitbook_refresh"
COOKIE_PATH = "/api/v1/auth"
# Browsers cannot add custom headers cross-site without CORS approval, so requiring this
# header on cookie-based refresh blocks CSRF on top of SameSite=Strict.
CSRF_HEADER = "x-chitbook-client"


def _token_response(tokens: service.IssuedTokens, client: ClientType, response: Response) -> TokenResponse:
    s = get_settings()
    refresh_in_body: str | None = tokens.refresh_token
    if client == ClientType.WEB:
        response.set_cookie(
            REFRESH_COOKIE,
            tokens.refresh_token,
            max_age=s.refresh_token_ttl_days * 86400,
            path=COOKIE_PATH,
            httponly=True,
            secure=s.refresh_cookie_secure,
            samesite="strict",
        )
        refresh_in_body = None
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        refresh_token=refresh_in_body,
        refresh_expires_at=tokens.refresh_expires_at,
        user=UserOut.model_validate(tokens.user),
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit("register"))],
    summary="Create an account (always MEMBER role)",
    responses=errors(
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.AUTH_WEAK_PASSWORD,
        ErrorCode.USERNAME_TAKEN,
        ErrorCode.EMAIL_TAKEN,
        ErrorCode.RATE_LIMITED,
    ),
)
async def register(body: UserCreate, request: Request, session: SessionDep) -> object:
    user = await users_service.register(session, body)
    await repository.record_event(
        session, request, AuthEvent.REGISTERED, user_id=user.id, username=user.username
    )
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(auth_rate_limit("login"))],
    summary="Sign in and get an access + refresh token",
    responses=errors(
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.AUTH_INVALID_CREDENTIALS,
        ErrorCode.AUTH_ACCOUNT_LOCKED,
        ErrorCode.RATE_LIMITED,
    ),
)
async def login(
    body: LoginRequest, request: Request, response: Response, session: SessionDep
) -> TokenResponse:
    tokens = await service.login(session, request, body)
    return _token_response(tokens, body.client, response)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(auth_rate_limit("refresh"))],
    summary="Swap a refresh token for a new access + refresh token (rotation)",
    responses=errors(
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.AUTH_REFRESH_INVALID,
        ErrorCode.AUTH_REFRESH_REUSED,
        ErrorCode.RATE_LIMITED,
    ),
)
async def refresh(
    body: RefreshRequest, request: Request, response: Response, session: SessionDep
) -> TokenResponse:
    raw = body.refresh_token
    if body.client == ClientType.WEB:
        if request.headers.get(CSRF_HEADER) != "web":
            raise AppError(ErrorCode.AUTH_REFRESH_INVALID, "Missing client header for cookie refresh")
        raw = request.cookies.get(REFRESH_COOKIE)
    tokens = await service.refresh(session, request, raw)
    return _token_response(tokens, body.client, response)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out this device",
    responses=errors(*AUTHED),
)
async def logout(request: Request, response: Response, session: SessionDep, user: CurrentUser) -> None:
    await service.logout(session, request, user, request.state.session_family)
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)


@router.get("/me", response_model=UserOut, summary="Get the signed-in user", responses=errors(*AUTHED))
async def me(user: CurrentUser) -> object:
    return user


@router.get(
    "/sessions",
    response_model=list[SessionOut],
    summary="List my signed-in devices",
    responses=errors(*AUTHED),
)
async def list_sessions(request: Request, session: SessionDep, user: CurrentUser) -> list[SessionOut]:
    rows = await repository.list_active(session, user.id)
    current = request.state.session_family
    return [
        SessionOut(
            id=row.family_id,
            device_name=row.device_name,
            user_agent=row.user_agent,
            ip_address=row.ip_address,
            signed_in_at=signed_in_at,
            last_used_at=row.last_used_at,
            expires_at=row.expires_at,
            current=row.family_id == current,
        )
        for row, signed_in_at in rows
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out one of my devices",
    responses=errors(*AUTHED, ErrorCode.VALIDATION_ERROR, ErrorCode.AUTH_SESSION_NOT_FOUND),
)
async def revoke_session(
    session_id: uuid.UUID, request: Request, session: SessionDep, user: CurrentUser
) -> None:
    await service.revoke_session(session, request, user, session_id)
