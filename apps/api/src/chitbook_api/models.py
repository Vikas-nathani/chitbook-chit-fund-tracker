"""Imports every model so SQLAlchemy metadata (and Alembic autogenerate) sees all tables."""

from chitbook_api.core.db import Base
from chitbook_api.modules.auctions.models import Auction
from chitbook_api.modules.auth.models import AuthAuditLog, AuthSession
from chitbook_api.modules.chat.models import ChatMessage
from chitbook_api.modules.funds.models import Fund
from chitbook_api.modules.groups.models import ChitGroup, Membership
from chitbook_api.modules.ledger.models import LedgerEntry
from chitbook_api.modules.loans.models import MemberLoan
from chitbook_api.modules.media.models import GroupMedia
from chitbook_api.modules.notifications.models import Notification, NotificationConfig
from chitbook_api.modules.payments.models import Payment
from chitbook_api.modules.polls.models import Poll, PollOption, PollVote
from chitbook_api.modules.simple_chits.models import (
    SimpleChit,
    SimpleChitEntry,
    SimpleChitMember,
    SimpleChitPayout,
)
from chitbook_api.modules.users.models import User

__all__ = [
    "Auction", "AuthAuditLog", "AuthSession", "Base", "ChatMessage", "ChitGroup", "Fund", "GroupMedia",
    "LedgerEntry", "MemberLoan", "Membership", "Notification", "NotificationConfig", "Payment", "Poll",
    "PollOption", "PollVote", "SimpleChit", "SimpleChitEntry", "SimpleChitMember", "SimpleChitPayout", "User",
]  # fmt: skip
