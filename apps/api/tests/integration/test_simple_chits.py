"""Simple Chits end-to-end through the HTTP API (includes ports of the original service tests)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

API = "/api/v1/simple-chits"


@pytest.fixture
async def owner(make_user: Any) -> dict[str, Any]:
    return await make_user("vasu")  # type: ignore[no-any-return]


async def create(client: httpx.AsyncClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    body = {
        "name": "Family chit",
        "totalAmount": 500000,
        "months": 20,
        "startMonth": "2026-08",
        "members": [{"name": "Ramesh", "shares": 2}, {"name": "Priya"}],
        **overrides,
    }
    r = await client.post(API, json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


# ---------------------------------------------------------------- ported from SimpleChitServiceTest


async def test_create_applies_shares_and_default_per_share(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(client, owner["headers"])
    assert chit["perShareAmount"] == 25000.0
    ramesh, priya = chit["members"]
    assert ramesh["shares"] == 2 and ramesh["startMonth"] == "2026-08"
    assert ramesh["amounts"][0] == ramesh["amounts"][19] == 50000.0
    assert priya["shares"] == 1 and priya["amounts"][0] == 25000.0


async def test_create_leaves_months_before_start_empty(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(
        client,
        owner["headers"],
        totalAmount=250000,
        months=10,
        members=[{"name": "Late", "startMonth": "2026-11"}],
    )
    late = chit["members"][0]
    assert late["startMonth"] == "2026-11"
    assert late["amounts"][:3] == [None, None, None]
    assert late["amounts"][3] == late["amounts"][9] == 25000.0


async def test_add_member_starts_at_given_month(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(client, owner["headers"])
    r = await client.post(
        f"{API}/{chit['id']}/members", json={"name": "NewPerson", "shares": 1, "startMonth": "2026-11"},
        headers=owner["headers"],
    )  # fmt: skip
    assert r.status_code == 200, r.text
    members = r.json()["members"]
    assert len(members) == 3
    added = members[2]
    assert (added["name"], added["startMonth"]) == ("NewPerson", "2026-11")
    assert added["amounts"][0] is None and added["amounts"][3] == 25000.0
    assert members[0]["amounts"][0] == 50000.0


async def test_other_users_cannot_see_or_change_my_chit(
    client: httpx.AsyncClient, owner: Any, make_user: Any
) -> None:
    chit = await create(client, owner["headers"])
    stranger = await make_user("kiran")
    for method, path in [("GET", ""), ("POST", "/members"), ("DELETE", "")]:
        r = await client.request(
            method, f"{API}/{chit['id']}{path}", headers=stranger["headers"], json={"name": "X"}
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "CHIT_NOT_FOUND"


async def test_payout_with_escalation_bumps_only_takers_later_months(
    client: httpx.AsyncClient, owner: Any
) -> None:
    chit = await create(client, owner["headers"], escalationEnabled=True, escalationPercent=1)
    ramesh_id = chit["members"][0]["id"]
    r = await client.put(
        f"{API}/{chit['id']}/payouts/5", json={"memberId": ramesh_id, "amount": 500000, "paidOn": "2026-12-01"},
        headers=owner["headers"],
    )  # fmt: skip
    assert r.status_code == 200, r.text
    ramesh = r.json()["members"][0]
    # base 50,000 (2 shares); months 6-20 get +500000 x 1% = 5,000
    assert ramesh["amounts"][3] == ramesh["amounts"][4] == 50000.0
    assert ramesh["amounts"][5] == ramesh["amounts"][19] == 55000.0
    assert r.json()["members"][1]["amounts"][5] == 25000.0


async def test_delete_payout_reverses_escalation_exactly(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(client, owner["headers"], escalationEnabled=True)
    ramesh_id = chit["members"][0]["id"]
    await client.put(f"{API}/{chit['id']}/payouts/5", json={"memberId": ramesh_id, "amount": 500000},
                     headers=owner["headers"])  # fmt: skip
    r = await client.delete(f"{API}/{chit['id']}/payouts/5", headers=owner["headers"])
    assert r.status_code == 200
    ramesh = r.json()["members"][0]
    assert ramesh["amounts"][5] == ramesh["amounts"][19] == 50000.0
    assert r.json()["payouts"] == []


async def test_replacing_payout_moves_escalation_to_new_taker(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(client, owner["headers"], escalationEnabled=True)
    ramesh_id, priya_id = (m["id"] for m in chit["members"])
    url = f"{API}/{chit['id']}/payouts/5"
    await client.put(url, json={"memberId": ramesh_id, "amount": 500000}, headers=owner["headers"])
    r = await client.put(url, json={"memberId": priya_id, "amount": 500000}, headers=owner["headers"])
    ramesh, priya = r.json()["members"]
    assert ramesh["amounts"][5] == 50000.0  # bump reversed
    assert priya["amounts"][5] == 30000.0  # bump applied once, not doubled
    assert r.json()["payouts"][0]["memberName"] == "Priya"


# ---------------------------------------------------------------- more behaviour


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"name": " "}, "Chit name is required"),
        ({"months": 0}, "Months must be between 1 and 120"),
        ({"members": []}, "Add between 1 and 100 members"),
        ({"commissionPercent": 25}, "Commission must be between 0 and 20%"),
        ({"startMonth": "Aug-2026"}, "Start month must be in yyyy-MM format"),
        ({"members": [{"name": "A", "startMonth": "2030-01"}]}, "Start month must fall within"),
    ],
)
async def test_create_validation(
    client: httpx.AsyncClient, owner: Any, overrides: dict[str, Any], message: str
) -> None:
    body = {
        "name": "C",
        "totalAmount": 1000,
        "months": 10,
        "startMonth": "2026-08",
        "members": [{"name": "A"}],
    }
    r = await client.post(API, json={**body, **overrides}, headers=owner["headers"])
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "CHIT_INVALID_INPUT"
    assert message in r.json()["error"]["message"]


async def test_mark_paid_updates_month_summary_and_list(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(client, owner["headers"], startMonth="2020-01", months=3, totalAmount=3000,
                        members=[{"name": "A"}, {"name": "B"}])  # fmt: skip
    a_id = chit["members"][0]["id"]
    r = await client.patch(
        f"{API}/{chit['id']}", json={"entries": [{"memberId": a_id, "month": 1, "paid": True}]},
        headers=owner["headers"],
    )  # fmt: skip
    assert r.status_code == 200, r.text
    month1 = r.json()["monthSummaries"][0]
    assert (month1["due"], month1["collected"], month1["pending"], month1["isDue"]) == (
        2000.0,
        1000.0,
        1000.0,
        True,
    )

    listing = (await client.get(API, headers=owner["headers"])).json()
    assert listing[0]["collected"] == 1000.0
    assert listing[0]["monthsElapsed"] == 3
    assert listing[0]["overdue"] == 5000.0


async def test_stats(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(client, owner["headers"], startMonth="2020-01", months=2, totalAmount=2000,
                        members=[{"name": "A"}], commissionPercent=5)  # fmt: skip
    a_id = chit["members"][0]["id"]
    await client.patch(f"{API}/{chit['id']}", json={"entries": [{"memberId": a_id, "month": 1, "paid": True}]},
                       headers=owner["headers"])  # fmt: skip
    await client.put(f"{API}/{chit['id']}/payouts/1", json={"memberId": a_id, "amount": 900},
                     headers=owner["headers"])  # fmt: skip

    stats = (await client.get(f"{API}/stats", headers=owner["headers"])).json()
    totals = stats["totals"]
    assert totals["chits"] == 1
    assert (totals["dueToDate"], totals["collected"], totals["paidOut"]) == (2000.0, 1000.0, 900.0)
    assert totals["cashInHand"] == 100.0 and totals["profit"] == 100.0
    assert totals["expectedCommission"] == 200.0  # 2000 x 5% x 2 months
    assert totals["collectionRate"] == 0.5
    assert stats["monthly"][0]["month"] == "2020-01"
    assert stats["monthly"][0]["cumulativePnl"] == 100.0
    due = stats["pendingDues"][0]
    assert (due["calendarMonth"], due["overdue"]) == ("2020-02", True)
    assert due["daysOverdue"] > 2000


async def test_delete_chit(client: httpx.AsyncClient, owner: Any) -> None:
    chit = await create(client, owner["headers"])
    await client.put(f"{API}/{chit['id']}/payouts/1", json={"memberId": chit["members"][0]["id"], "amount": 1},
                     headers=owner["headers"])  # fmt: skip
    assert (await client.delete(f"{API}/{chit['id']}", headers=owner["headers"])).status_code == 204
    assert (await client.get(f"{API}/{chit['id']}", headers=owner["headers"])).status_code == 404
