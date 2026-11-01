"""Payments, funds, ledger (+PDF), auctions, loans and reports."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import httpx

from chitbook_api.core.time import now

API = "/api/v1"


async def test_payments_flow_and_audit(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    mine = await client.post(
        f"{API}/payments",
        json={"userId": member["user"]["id"], "chitGroupId": g["id"], "month": "2026-08", "amountPaid": 5000,
              "mode": "upi"},
        headers=member["headers"],
    )  # fmt: skip
    assert mine.status_code == 201, mine.text
    assert (mine.json()["status"], mine.json()["mode"], mine.json()["verified"]) == (
        "COMPLETED",
        "UPI",
        False,
    )

    for_lead = await client.post(
        f"{API}/payments",
        json={"userId": lead["user"]["id"], "chitGroupId": g["id"], "month": "2026-08", "amountPaid": 5000,
              "mode": "CASH"},
        headers=member["headers"],
    )  # fmt: skip
    assert for_lead.status_code == 403 and for_lead.json()["error"]["code"] == "PAYMENT_NOT_ALLOWED"

    cannot_verify = await client.post(f"{API}/payments/{mine.json()['id']}/verify", headers=member["headers"])
    assert cannot_verify.json()["error"]["code"] == "PAYMENT_VERIFY_NOT_ALLOWED"

    audit = (await client.get(f"{API}/reports/group/{g['id']}/audit", headers=lead["headers"])).json()
    assert audit["unverifiedPaymentsCount"] == 1 and audit["totalUnverifiedAmount"] == 5000.0

    verified = await client.post(f"{API}/payments/{mine.json()['id']}/verify", headers=lead["headers"])
    assert verified.json()["verified"] is True and verified.json()["verifiedByUserName"] == "Lead"

    summary = (await client.get(f"{API}/reports/group/{g['id']}/summary", headers=member["headers"])).json()
    assert summary["totalContributionsCollected"] == 5000.0 and summary["totalMembers"] == 2

    assert len((await client.get(f"{API}/payments/group/{g['id']}", headers=lead["headers"])).json()) == 1
    member_view = await client.get(f"{API}/payments/group/{g['id']}/user/{member['user']['id']}",
                                   headers=member["headers"])  # fmt: skip
    assert len(member_view.json()) == 1


async def test_funds(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    fund = (await client.get(f"{API}/funds/group/{g['id']}", headers=member["headers"])).json()
    assert fund["id"] == g["fundId"] and fund["totalAmount"] == 0.0
    denied = await client.patch(
        f"{API}/funds/{fund['id']}", json={"totalAmount": 1}, headers=member["headers"]
    )
    assert denied.status_code == 403
    updated = await client.patch(f"{API}/funds/{fund['id']}", json={"totalAmount": 120000, "interestRate": 12},
                                 headers=lead["headers"])  # fmt: skip
    assert (updated.json()["totalAmount"], updated.json()["interestRate"]) == (120000.0, 12.0)
    assert len((await client.get(f"{API}/funds", headers=member["headers"])).json()) == 1
    assert (await client.get(f"{API}/funds", headers=group_setup["outsider"]["headers"])).json() == []


async def test_ledger_and_pdf(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    r = await client.post(
        f"{API}/ledger",
        json={"userId": member["user"]["id"], "chitGroupId": g["id"], "entryType": "CREDIT", "amount": 5000,
              "remark": "August contribution"},
        headers=lead["headers"],
    )  # fmt: skip
    assert r.status_code == 201, r.text
    mine = await client.get(
        f"{API}/ledger?groupId={g['id']}&userId={member['user']['id']}", headers=member["headers"]
    )
    assert len(mine.json()) == 1
    assert (await client.get(f"{API}/ledger?groupId={g['id']}", headers=member["headers"])).status_code == 403
    assert (await client.get(f"{API}/ledger", headers=member["headers"])).status_code == 403

    pdf = await client.get(f"{API}/ledger/pdf?groupId={g['id']}", headers=lead["headers"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


async def test_auctions(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    body = {"chitGroupId": g["id"], "winningMemberId": member["user"]["id"], "month": "2026-08",
            "winningAmount": 45000, "commission": 2500}  # fmt: skip
    assert (await client.post(f"{API}/auctions", json=body, headers=member["headers"])).status_code == 403
    r = await client.post(f"{API}/auctions", json=body, headers=lead["headers"])
    assert r.status_code == 201, r.text
    assert r.json()["winningMemberName"] == "Member"
    dup = await client.post(f"{API}/auctions", json=body, headers=lead["headers"])
    assert dup.json()["error"]["code"] == "AUCTION_EXISTS"
    outsider = {**body, "month": "2026-09", "winningMemberId": group_setup["outsider"]["user"]["id"]}
    assert (await client.post(f"{API}/auctions", json=outsider, headers=lead["headers"])).status_code == 403

    assert len((await client.get(f"{API}/auctions/group/{g['id']}", headers=member["headers"])).json()) == 1
    won = await client.get(f"{API}/auctions/winner/{member['user']['id']}", headers=member["headers"])
    assert len(won.json()) == 1

    auction_id = r.json()["id"]
    assert (await client.get(f"{API}/auctions/{auction_id}", headers=member["headers"])).status_code == 200
    assert (await client.delete(f"{API}/auctions/{auction_id}", headers=member["headers"])).status_code == 403
    assert (await client.delete(f"{API}/auctions/{auction_id}", headers=lead["headers"])).status_code == 204
    gone = await client.get(f"{API}/auctions/{auction_id}", headers=lead["headers"])
    assert gone.json()["error"]["code"] == "AUCTION_NOT_FOUND"


async def test_loans_daily_interest(client: httpx.AsyncClient, group_setup: Any) -> None:
    g, lead, member = group_setup["group"], group_setup["lead"], group_setup["member"]
    start = (now() - timedelta(days=73)).isoformat()
    r = await client.post(
        f"{API}/loans",
        json={"userId": member["user"]["id"], "chitGroupId": g["id"], "principal": 100000, "interestRate": 12,
              "tenureMonths": 12, "startDate": start},
        headers=lead["headers"],
    )  # fmt: skip
    assert r.status_code == 201, r.text
    # 100000 x 12 x 73 / 36500 = 2400
    assert r.json()["currentPayable"] == 102400.0

    payable = await client.get(f"{API}/loans/group/{g['id']}/user/{member['user']['id']}/payable",
                               headers=member["headers"])  # fmt: skip
    assert payable.json()["currentPayable"] == 102400.0
    assert (
        len((await client.get(f"{API}/loans/user/{member['user']['id']}", headers=member["headers"])).json())
        == 1
    )

    closed = await client.put(
        f"{API}/loans/{r.json()['id']}/status", json={"status": "PAID"}, headers=lead["headers"]
    )
    assert closed.json()["status"] == "PAID" and closed.json()["currentPayable"] == 102400.0

    report = (
        await client.get(f"{API}/reports/user/{member['user']['id']}", headers=member["headers"])
    ).json()
    assert report[0]["currentLoanPayable"] == 102400.0
