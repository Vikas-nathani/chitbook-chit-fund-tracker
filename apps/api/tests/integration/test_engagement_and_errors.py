"""Polls, media, chat, notifications, plus the error envelope, request ids and logging."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from chitbook_api.core.config import get_settings

API = "/api/v1"


async def test_polls(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    r = await client.post(f"{API}/polls", json={"groupId": g["id"], "question": "Meet on Sunday?",
                                                "options": ["Yes", "No"]}, headers=member["headers"])  # fmt: skip
    assert r.status_code == 201, r.text
    poll = r.json()
    assert poll["creatorName"] == "Member"
    yes = poll["options"][0]["id"]

    voted = await client.post(
        f"{API}/polls/vote", json={"pollId": poll["id"], "optionId": yes}, headers=lead["headers"]
    )
    assert voted.json()["options"][0]["voteCount"] == 1 and voted.json()["myVoteOptionId"] == yes
    twice = await client.post(
        f"{API}/polls/vote", json={"pollId": poll["id"], "optionId": yes}, headers=lead["headers"]
    )
    assert twice.json()["error"]["code"] == "POLL_ALREADY_VOTED"

    await client.put(f"{API}/polls/{poll['id']}/close", headers=member["headers"])
    late = await client.post(f"{API}/polls/vote", json={"pollId": poll["id"], "optionId": yes},
                             headers=member["headers"])  # fmt: skip
    assert late.json()["error"]["code"] == "POLL_CLOSED"
    outsider = await client.get(f"{API}/polls/group/{g['id']}", headers=group_setup["outsider"]["headers"])
    assert outsider.status_code == 403


async def test_media(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    r = await client.post(f"{API}/media", json={"groupId": g["id"], "url": "https://example.com/a.jpg",
                                                "caption": "Meeting", "mediaType": "IMAGE"},
                          headers=member["headers"])  # fmt: skip
    assert r.status_code == 201, r.text
    assert r.json()["uploaderName"] == "Member"
    bad = await client.post(f"{API}/media", json={"groupId": g["id"], "url": "javascript:alert(1)", "caption": "x",
                                                  "mediaType": "IMAGE"}, headers=member["headers"])  # fmt: skip
    assert bad.status_code == 422
    assert (await client.delete(f"{API}/media/{r.json()['id']}", headers=lead["headers"])).status_code == 204


async def test_chat_rest(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    first = await client.post(f"{API}/chat/group/{g['id']}/messages", json={"content": "Hello"},
                              headers=member["headers"])  # fmt: skip
    assert first.status_code == 201, first.text
    await client.post(f"{API}/chat/group/{g['id']}/messages", json={"content": "Hi"}, headers=lead["headers"])

    all_msgs = (await client.get(f"{API}/chat/group/{g['id']}/messages", headers=member["headers"])).json()
    assert [m["content"] for m in all_msgs] == ["Hello", "Hi"]
    newer = await client.get(f"{API}/chat/group/{g['id']}/messages?afterId={first.json()['id']}",
                             headers=member["headers"])  # fmt: skip
    assert [m["content"] for m in newer.json()] == ["Hi"]
    denied = await client.post(f"{API}/chat/group/{g['id']}/messages", json={"content": "x"},
                               headers=group_setup["outsider"]["headers"])  # fmt: skip
    assert denied.status_code == 403


async def test_notifications_read(client: httpx.AsyncClient, group_setup: Any) -> None:
    lead = group_setup["lead"]
    await client.post(f"{API}/groups/join", json={"groupCode": group_setup["group"]["groupCode"]},
                      headers=group_setup["outsider"]["headers"])  # fmt: skip
    uid = lead["user"]["id"]
    count = (await client.get(f"{API}/notifications/user/{uid}/unread-count", headers=lead["headers"])).json()
    assert count == {"count": 1}
    note = (
        await client.get(f"{API}/notifications/user/{uid}?unreadOnly=true", headers=lead["headers"])
    ).json()[0]
    assert (await client.put(f"{API}/notifications/{note['id']}/read", headers=lead["headers"])).json()[
        "status"
    ] == "READ"
    unread = await client.get(f"{API}/notifications/user/{uid}?unreadOnly=true", headers=lead["headers"])
    assert unread.json() == []
    assert len((await client.get(f"{API}/notifications/user/{uid}", headers=lead["headers"])).json()) == 1
    snoop = await client.get(f"{API}/notifications/user/{uid}", headers=group_setup["member"]["headers"])
    assert snoop.status_code == 403


async def test_error_envelope_request_id_and_log_line(
    client: httpx.AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    r = await client.get(f"{API}/no-such-route", headers={"X-Request-ID": "test-req-12345"})
    assert r.status_code == 404
    assert r.json() == {
        "error": {"code": "NOT_FOUND", "message": "Requested resource was not found", "details": None,
                  "requestId": "test-req-12345"}
    }  # fmt: skip
    assert r.headers["x-request-id"] == "test-req-12345"
    assert r.headers["x-content-type-options"] == "nosniff"

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    access = [
        x for x in lines if x.get("event") == "http.request" and x.get("request_id") == "test-req-12345"
    ]
    assert access and access[-1]["status"] == 404 and access[-1]["timestamp"].endswith("+05:30")


async def test_validation_error_lists_fields(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{API}/auth/register", json={"name": "x"})
    assert r.status_code == 422
    fields = {d["field"] for d in r.json()["error"]["details"]}
    assert {"username", "email", "password"} <= fields


async def test_passwords_never_reach_the_logs(
    client: httpx.AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    await client.post(f"{API}/auth/login", json={"username": "someone", "password": "SuperSecret-77"})
    out = capsys.readouterr().out
    assert "auth.login_failed" in out  # the attempt was logged...
    assert "SuperSecret-77" not in out  # ...without the password


def test_every_route_declares_its_errors() -> None:
    """Each route lists its errors with responses=errors(...); they show up in OpenAPI."""
    from chitbook_api.main import create_app

    spec = create_app().openapi()
    login = spec["paths"]["/api/v1/auth/login"]["post"]["responses"]
    assert "AUTH_INVALID_CREDENTIALS" in login["401"]["content"]["application/json"]["examples"]
    assert "AUTH_ACCOUNT_LOCKED" in login["429"]["content"]["application/json"]["examples"]
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            assert "500" in op["responses"], f"{method.upper()} {path} has no responses=errors(...)"


async def test_health(client: httpx.AsyncClient) -> None:
    assert (await client.get("/health")).json()["status"] == "ok"
    ready = (await client.get("/health/ready")).json()
    assert ready["database"] == f"ok (timezone={get_settings().tz})"
