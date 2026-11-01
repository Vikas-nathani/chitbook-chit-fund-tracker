from __future__ import annotations

from typing import Any

import httpx

API = "/api/v1"


async def test_create_group_makes_creator_admin_and_fund(client: httpx.AsyncClient, group_setup: Any) -> None:
    group, lead = group_setup["group"], group_setup["lead"]
    assert group["groupCode"].startswith("CHIT") and len(group["groupCode"]) == 10
    assert group["status"] == "PENDING"
    assert group["fundId"] is not None

    members = (await client.get(f"{API}/groups/{group['id']}/members", headers=lead["headers"])).json()
    roles = {m["userName"]: m["role"] for m in members}
    assert roles == {"Lead": "ADMIN", "Member": "MEMBER"}


async def test_outsider_is_blocked_and_member_cannot_admin(
    client: httpx.AsyncClient, group_setup: Any
) -> None:
    gid = group_setup["group"]["id"]
    r = await client.get(f"{API}/groups/{gid}", headers=group_setup["outsider"]["headers"])
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_GROUP_MEMBER"
    r = await client.patch(
        f"{API}/groups/{gid}", json={"name": "X"}, headers=group_setup["member"]["headers"]
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "NOT_GROUP_ADMIN"


async def test_join_by_code_is_pending_and_notifies_admin(
    client: httpx.AsyncClient, group_setup: Any
) -> None:
    group, lead, outsider = group_setup["group"], group_setup["lead"], group_setup["outsider"]
    r = await client.post(f"{API}/groups/join", json={"groupCode": group["groupCode"].lower()},
                          headers=outsider["headers"])  # fmt: skip
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "PENDING"

    again = await client.post(
        f"{API}/groups/join", json={"groupCode": group["groupCode"]}, headers=outsider["headers"]
    )
    assert again.json()["error"]["code"] == "MEMBERSHIP_PENDING"

    notes = (
        await client.get(f"{API}/notifications/user/{lead['user']['id']}", headers=lead["headers"])
    ).json()
    assert notes[0]["type"] == "JOIN_REQUEST" and "Outsider" in notes[0]["message"]

    # pending members are visible to admins only
    as_member = await client.get(
        f"{API}/groups/{group['id']}/members", headers=group_setup["member"]["headers"]
    )
    assert len(as_member.json()) == 2
    as_admin = await client.get(f"{API}/groups/{group['id']}/members", headers=lead["headers"])
    assert len(as_admin.json()) == 3

    approve = await client.put(
        f"{API}/groups/{group['id']}/members/{outsider['user']['id']}/status", json={"status": "ACTIVE"},
        headers=lead["headers"],
    )  # fmt: skip
    assert approve.json()["status"] == "ACTIVE"
    assert (await client.get(f"{API}/groups/{group['id']}", headers=outsider["headers"])).status_code == 200


async def test_group_member_limit(client: httpx.AsyncClient, group_setup: Any, make_user: Any) -> None:
    gid, lead = group_setup["group"]["id"], group_setup["lead"]
    third = await make_user("third")
    fourth = await make_user("fourth")
    assert (await client.post(f"{API}/groups/{gid}/members", json={"userId": third["user"]["id"]},
                              headers=lead["headers"])).status_code == 201  # fmt: skip
    full = await client.post(f"{API}/groups/{gid}/members", json={"userId": fourth["user"]["id"]},
                             headers=lead["headers"])  # fmt: skip
    assert full.status_code == 409 and full.json()["error"]["code"] == "GROUP_FULL"


async def test_list_search_and_admin_sees_all(
    client: httpx.AsyncClient, group_setup: Any, admin_headers: Any
) -> None:
    member = group_setup["member"]
    assert len((await client.get(f"{API}/groups?name=office", headers=member["headers"])).json()) == 1
    assert (await client.get(f"{API}/groups?name=zzz", headers=member["headers"])).json() == []
    assert (await client.get(f"{API}/groups", headers=group_setup["outsider"]["headers"])).json() == []
    assert len((await client.get(f"{API}/groups?status=PENDING", headers=admin_headers)).json()) == 1


async def test_users_visibility(client: httpx.AsyncClient, group_setup: Any) -> None:
    names = {
        u["username"]
        for u in (await client.get(f"{API}/users", headers=group_setup["member"]["headers"])).json()
    }
    assert names == {"lead", "member"}
    r = await client.get(
        f"{API}/users/{group_setup['lead']['user']['id']}", headers=group_setup["member"]["headers"]
    )
    assert r.status_code == 403


async def test_remove_member_and_delete_own_account(client: httpx.AsyncClient, group_setup: Any) -> None:
    gid, lead, member = group_setup["group"]["id"], group_setup["lead"], group_setup["member"]
    uid = member["user"]["id"]
    assert (
        await client.delete(f"{API}/groups/{gid}/members/{uid}", headers=lead["headers"])
    ).status_code == 204
    assert (await client.get(f"{API}/groups/{gid}", headers=member["headers"])).status_code == 403

    # users can delete only their own account (unless platform admin)
    other = await client.delete(f"{API}/users/{lead['user']['id']}", headers=member["headers"])
    assert other.json()["error"]["code"] == "FORBIDDEN"
    assert (await client.delete(f"{API}/users/{uid}", headers=member["headers"])).status_code == 204
    assert (await client.get(f"{API}/auth/me", headers=member["headers"])).status_code == 401


async def test_delete_group_cascades(client: httpx.AsyncClient, group_setup: Any) -> None:
    gid, lead = group_setup["group"]["id"], group_setup["lead"]
    assert (await client.delete(f"{API}/groups/{gid}", headers=lead["headers"])).status_code == 204
    assert (await client.get(f"{API}/groups/{gid}", headers=lead["headers"])).json()["error"][
        "code"
    ] == "GROUP_NOT_FOUND"
