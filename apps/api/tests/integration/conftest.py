from __future__ import annotations

from typing import Any

import httpx
import pytest


@pytest.fixture
async def group_setup(client: httpx.AsyncClient, make_user: Any) -> dict[str, Any]:
    """`lead` creates a group (becomes group ADMIN); `member` is added as an ACTIVE member;
    `outsider` has an account but no membership."""
    lead = await make_user("lead")
    member = await make_user("member")
    outsider = await make_user("outsider")
    r = await client.post(
        "/api/v1/groups",
        json={"name": "Office chit", "duration": 10, "monthlyAmount": 5000, "totalMembers": 3},
        headers=lead["headers"],
    )
    assert r.status_code == 201, r.text
    group = r.json()
    r = await client.post(
        f"/api/v1/groups/{group['id']}/members",
        json={"userId": member["user"]["id"]},
        headers=lead["headers"],
    )
    assert r.status_code == 201, r.text
    return {"lead": lead, "member": member, "outsider": outsider, "group": group}
