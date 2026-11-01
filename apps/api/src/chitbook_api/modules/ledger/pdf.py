"""Renders ledger entries as a PDF report (A4, table of entries + totals)."""

from __future__ import annotations

import io
from collections.abc import Sequence
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from chitbook_api.core.time import now, to_app_tz
from chitbook_api.modules.ledger.models import EntryType, LedgerEntry


def render(entries: Sequence[LedgerEntry], title: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=title)
    styles = getSampleStyleSheet()

    rows: list[list[str]] = [["#", "Date", "Member", "Group", "Type", "Amount", "Remark"]]
    credit = debit = Decimal("0")
    for e in entries:
        rows.append(
            [
                str(e.id),
                to_app_tz(e.entry_date).strftime("%d-%m-%Y"),
                e.user.name,
                e.group.name,
                e.entry_type.value,
                f"{e.amount:,.2f}",
                (e.remark or "")[:40],
            ]
        )
        if e.entry_type == EntryType.CREDIT:
            credit += e.amount
        else:
            debit += e.amount

    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (5, 1), (5, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ]
        )
    )
    story = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"Generated on {now().strftime('%d-%m-%Y %H:%M')} IST", styles["Normal"]),
        Paragraph(
            f"Entries: {len(entries)} &nbsp; Credit: {credit:,.2f} &nbsp; Debit: {debit:,.2f} &nbsp; "
            f"Net: {credit - debit:,.2f}",
            styles["Normal"],
        ),
        Spacer(1, 12),
        table,
    ]
    doc.build(story)
    return buffer.getvalue()
