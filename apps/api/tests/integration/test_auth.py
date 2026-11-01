from __future__ import annotations

from typing import Any

import httpx

from tests.conftest import ADMIN, LoginFn

API = "/api/v1"


def bearer(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['accessToken']}"}


async def test_admin_is_bootstrapped_and_can_sign_in(client: httpx.AsyncClient, login: LoginFn) -> None:
    tokens = await login(ADMIN["username"], ADMIN["password"])
    assert tokens["tokenType"] == "Bearer"
    assert tokens["refreshToken"]
    assert tokens["user"]["role"] == "ADMIN"
    assert tokens["user"]["createdAt"].endswith("+05:30")  # IST everywhere

    me = await client.get(f"{API}/auth/me", headers=bearer(tokens))
    assert me.status_code == 200
    assert me.json()["username"] == ADMIN["username"]


async def test_register_always_creates_member(client: httpx.AsyncClient) -> None:
    r = await client.post(
        f"{API}/auth/register",
        json={"name": "Ramesh", "username": "Ramesh", "email": "R@Example.com", "password": "Ramesh-123",
              "role": "ADMIN"},
    )  # fmt: skip
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "MEMBER"
    assert body["username"] == "ramesh"  # usernames are case-insensitive
    assert body["email"] == "r@example.com"
    assert "passwordHash" not in body and "password" not in body


async def test_register_rejects_duplicates_and_weak_passwords(client: httpx.AsyncClient) -> None:
    payload = {"name": "A", "username": "anil", "email": "anil@example.com", "password": "Anil-1234"}
    assert (await client.post(f"{API}/auth/register", json=payload)).status_code == 201

    dup = await client.post(f"{API}/auth/register", json={**payload, "email": "x@example.com"})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "USERNAME_TAKEN"

    weak = await client.post(
        f"{API}/auth/register",
        json={**payload, "username": "anil2", "email": "a2@example.com", "password": "password1"},
    )
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "AUTH_WEAK_PASSWORD"


async def test_wrong_password_is_generic_and_audited(client: httpx.AsyncClient) -> None:
    r = await client.post(
        f"{API}/auth/login", json={"username": ADMIN["username"], "password": "nope-nope-1"}
    )
    unknown = await client.post(f"{API}/auth/login", json={"username": "ghost", "password": "nope-nope-1"})
    assert r.status_code == unknown.status_code == 401
    assert r.json()["error"]["code"] == unknown.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert r.json()["error"]["message"] == unknown.json()["error"]["message"]


async def test_missing_or_bad_token(client: httpx.AsyncClient) -> None:
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTH_REQUIRED"
    r = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.json()["error"]["code"] == "AUTH_TOKEN_INVALID"


async def test_refresh_rotates_and_reuse_revokes_the_chain(client: httpx.AsyncClient, login: LoginFn) -> None:
    first = await login(ADMIN["username"], ADMIN["password"])

    r = await client.post(f"{API}/auth/refresh", json={"refreshToken": first["refreshToken"]})
    assert r.status_code == 200, r.text
    second = r.json()
    assert second["refreshToken"] != first["refreshToken"]
    assert (await client.get(f"{API}/auth/me", headers=bearer(second))).status_code == 200

    # The old refresh token comes back (e.g. stolen copy): whole session chain is signed out
    reuse = await client.post(f"{API}/auth/refresh", json={"refreshToken": first["refreshToken"]})
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "AUTH_REFRESH_REUSED"

    newest = await client.post(f"{API}/auth/refresh", json={"refreshToken": second["refreshToken"]})
    assert newest.json()["error"]["code"] == "AUTH_REFRESH_INVALID"
    me = await client.get(f"{API}/auth/me", headers=bearer(second))
    assert me.json()["error"]["code"] == "AUTH_SESSION_REVOKED"


async def test_logout_signs_out_immediately(client: httpx.AsyncClient, login: LoginFn) -> None:
    tokens = await login(ADMIN["username"], ADMIN["password"])
    assert (await client.post(f"{API}/auth/logout", headers=bearer(tokens))).status_code == 204
    assert (await client.get(f"{API}/auth/me", headers=bearer(tokens))).status_code == 401
    r = await client.post(f"{API}/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert r.status_code == 401


async def test_sessions_list_and_remote_sign_out(client: httpx.AsyncClient, login: LoginFn) -> None:
    phone = await login(ADMIN["username"], ADMIN["password"], deviceName="Phone")
    laptop = await login(ADMIN["username"], ADMIN["password"], deviceName="Laptop")

    sessions = (await client.get(f"{API}/auth/sessions", headers=bearer(phone))).json()
    assert {s["deviceName"] for s in sessions} == {"Phone", "Laptop"}
    assert [s["current"] for s in sessions if s["deviceName"] == "Phone"] == [True]

    laptop_id = next(s["id"] for s in sessions if s["deviceName"] == "Laptop")
    assert (await client.delete(f"{API}/auth/sessions/{laptop_id}", headers=bearer(phone))).status_code == 204
    assert (await client.get(f"{API}/auth/me", headers=bearer(laptop))).status_code == 401
    assert (await client.get(f"{API}/auth/me", headers=bearer(phone))).status_code == 200


async def test_lockout_after_repeated_failures(client: httpx.AsyncClient, make_user: Any) -> None:
    user = await make_user("sita")
    for _ in range(5):
        r = await client.post(f"{API}/auth/login", json={"username": "sita", "password": "Wrong-pass-1"})
        assert r.status_code == 401
    locked = await client.post(f"{API}/auth/login", json={"username": "sita", "password": user["password"]})
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "AUTH_ACCOUNT_LOCKED"
    assert locked.json()["error"]["details"]["retryAfterSeconds"] > 0


async def test_rate_limit_per_ip(client: httpx.AsyncClient) -> None:
    codes = [
        (
            await client.post(f"{API}/auth/login", json={"username": f"u{i}", "password": "Whatever-1"})
        ).status_code
        for i in range(12)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10:] == [429, 429]


async def test_web_client_gets_httponly_cookie_not_body_token(client: httpx.AsyncClient) -> None:
    r = await client.post(
        f"{API}/auth/login",
        json={"username": ADMIN["username"], "password": ADMIN["password"], "client": "web"},
    )
    assert r.json()["refreshToken"] is None
    cookie = r.headers["set-cookie"]
    assert "chitbook_refresh=" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie

    no_header = await client.post(f"{API}/auth/refresh", json={"client": "web"})
    assert no_header.status_code == 401  # CSRF guard: custom header required
    ok = await client.post(
        f"{API}/auth/refresh", json={"client": "web"}, headers={"X-Chitbook-Client": "web"}
    )
    assert ok.status_code == 200, ok.text


async def test_change_password_signs_out_other_devices(
    client: httpx.AsyncClient, make_user: Any, login: LoginFn
) -> None:
    user = await make_user("gopal")
    other = await login("gopal", user["password"])
    r = await client.put(
        f"{API}/users/{user['user']['id']}/password",
        headers=user["headers"],
        json={"currentPassword": user["password"], "newPassword": "Brand-new-99"},
    )
    assert r.status_code == 204
    assert (await client.get(f"{API}/auth/me", headers=bearer(other))).status_code == 401
    await login("gopal", "Brand-new-99")
