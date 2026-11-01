"""End-to-end smoke test against a running ChitBook API.

Usage (from the repo root, API running via docker compose):
    apps/api/.venv/bin/python scripts/smoke_test.py http://localhost:8080

Checks: health + DB timezone, admin login, refresh rotation + reuse detection, a full Simple
Chit flow (late member, escalation payout, reversal, stats), group chat over WebSocket, and
the error envelope. Creates a throwaway user and data; prints PASS/FAIL per step.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
from pathlib import Path
from typing import Any

import httpx
import websockets
from dotenv import dotenv_values

ENV = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
BASE = sys.argv[1] if len(sys.argv) > 1 else f"http://localhost:{ENV['API_PORT']}"
API = f"{BASE}/api/v1"
failures = 0


def check(name: str, ok: bool, detail: Any = "") -> None:
    global failures
    print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else f'  -> {detail}'}")
    failures += 0 if ok else 1


async def main() -> None:
    async with httpx.AsyncClient(timeout=20) as c:
        ready = (await c.get(f"{BASE}/health/ready")).json()
        check(
            "health/ready reports the .env timezone",
            ready.get("database") == f"ok (timezone={ENV['TZ']})",
            ready,
        )

        r = await c.post(f"{API}/auth/login", json={"username": ENV["ADMIN_USERNAME"], "password": ENV["ADMIN_PASSWORD"],
                                                  "deviceName": "smoke-test"})  # fmt: skip
        check("admin login", r.status_code == 200, r.text)
        first = r.json()
        r = await c.post(f"{API}/auth/refresh", json={"refreshToken": first["refreshToken"]})
        check(
            "refresh rotates the token",
            r.status_code == 200 and r.json()["refreshToken"] != first["refreshToken"],
        )
        r = await c.post(f"{API}/auth/refresh", json={"refreshToken": first["refreshToken"]})
        check(
            "reused refresh token is rejected",
            r.json().get("error", {}).get("code") == "AUTH_REFRESH_REUSED",
            r.text,
        )

        name = f"smoke{secrets.token_hex(3)}"
        password = f"Smoke-{secrets.token_hex(4)}1"
        r = await c.post(f"{API}/auth/register", json={"name": "Smoke", "username": name,
                                                     "email": f"{name}@example.com", "password": password})  # fmt: skip
        check("register user", r.status_code == 201, r.text)
        tokens = (await c.post(f"{API}/auth/login", json={"username": name, "password": password})).json()
        h = {"Authorization": f"Bearer {tokens['accessToken']}"}
        check(
            "timestamps are IST", tokens["user"]["createdAt"].endswith("+05:30"), tokens["user"]["createdAt"]
        )

        r = await c.post(f"{API}/simple-chits", headers=h, json={
            "name": "Smoke chit", "totalAmount": 500000, "months": 20, "startMonth": "2026-08",
            "escalationEnabled": True, "members": [{"name": "Ramesh", "shares": 2}, {"name": "Priya"}]})  # fmt: skip
        chit = r.json()
        check("create simple chit", r.status_code == 201 and chit["perShareAmount"] == 25000.0, r.text)
        r = await c.post(f"{API}/simple-chits/{chit['id']}/members", headers=h,
                         json={"name": "Late", "startMonth": "2026-11"})  # fmt: skip
        late = r.json()["members"][2]
        check("late joiner starts in Nov", late["amounts"][2] is None and late["amounts"][3] == 25000.0, late)
        ramesh = chit["members"][0]["id"]
        r = await c.put(
            f"{API}/simple-chits/{chit['id']}/payouts/5",
            headers=h,
            json={"memberId": ramesh, "amount": 500000},
        )
        check(
            "payout escalates taker's later months", r.json()["members"][0]["amounts"][5] == 55000.0, r.text
        )
        r = await c.delete(f"{API}/simple-chits/{chit['id']}/payouts/5", headers=h)
        check("deleting payout reverses escalation", r.json()["members"][0]["amounts"][5] == 50000.0, r.text)
        stats = (await c.get(f"{API}/simple-chits/stats", headers=h)).json()
        check("stats", stats["totals"]["chits"] == 1, stats.get("totals"))

        g = (await c.post(f"{API}/groups", headers=h, json={"name": "Smoke group", "duration": 10,
                                                         "monthlyAmount": 1000, "totalMembers": 5})).json()  # fmt: skip
        ws_url = API.replace("http", "ws", 1) + f"/chat/ws/groups/{g['id']}"
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"type": "auth", "token": tokens["accessToken"]}))
            check("websocket auth", json.loads(await ws.recv()) == {"type": "ready"})
            await c.post(
                f"{API}/chat/group/{g['id']}/messages", headers=h, json={"content": "hello over REST"}
            )
            pushed = json.loads(await asyncio.wait_for(ws.recv(), 10))
            check("REST message pushed live", pushed["data"]["content"] == "hello over REST", pushed)
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"type": "auth", "token": "bad"}))
            try:
                await asyncio.wait_for(ws.recv(), 5)
                check("websocket rejects bad token", False, "socket stayed open")
            except websockets.ConnectionClosed as closed:
                check(
                    "websocket rejects bad token",
                    closed.rcvd is not None and closed.rcvd.code == 4401,
                    closed,
                )

        r = await c.get(f"{API}/simple-chits/999999", headers=h)
        err = r.json().get("error", {})
        check(
            "error envelope has code + requestId",
            err.get("code") == "CHIT_NOT_FOUND" and err.get("requestId"),
            r.text,
        )
        check("security headers", r.headers.get("x-content-type-options") == "nosniff")

        await c.delete(f"{API}/groups/{g['id']}", headers=h)
        await c.delete(f"{API}/users/{tokens['user']['id']}", headers=h)

    print(f"\n{'ALL PASSED' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)


asyncio.run(main())
