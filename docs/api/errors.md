# Error codes

> Generated from `ErrorCode` in `apps/api/src/chitbook_api/core/errors.py`.

Every error response:

```json
{"error": {"code": "CHIT_NOT_FOUND", "message": "Chit not found", "details": null, "requestId": "5f2c..."}}
```

| Code | HTTP | Message | Exact problem / fix |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | Request data is invalid | Body/query/path does not match the schema. `details` lists each bad field and why. |
| `BAD_REQUEST` | 400 | Request is invalid | Malformed request (e.g. invalid JSON). |
| `NOT_FOUND` | 404 | Requested resource was not found | Wrong URL or method; check the path and the `/api/v1` prefix. |
| `METHOD_NOT_ALLOWED` | 405 | Method not allowed | Right path, wrong HTTP method. |
| `RATE_LIMITED` | 429 | Too many requests, try again later | More than RATE_LIMIT_AUTH_PER_MINUTE calls from one IP in 60 s. Wait a minute. |
| `DB_CONFLICT` | 409 | The change conflicts with existing data | A unique/foreign-key constraint failed (two requests raced, or bad ids). See the `db.integrity_error` log line. |
| `DB_UNAVAILABLE` | 503 | Database is unavailable | Postgres unreachable: host Postgres down, pg_hba.conf missing the Docker subnet, or wrong DB_* values in .env. See the `db.unavailable` log line. |
| `INTERNAL_ERROR` | 500 | An unexpected internal error occurred | A bug. Search `docker compose logs api` for the `requestId` and read the `request.unhandled_exception` line: it has the exception and stack trace. |
| `AUTH_REQUIRED` | 401 | Authentication required | No `Authorization: Bearer <token>` header. |
| `AUTH_TOKEN_INVALID` | 401 | Access token is invalid | Token malformed, signed with another JWT_SECRET (secret changed?), or user deleted. |
| `AUTH_TOKEN_EXPIRED` | 401 | Access token has expired | Access token older than ACCESS_TOKEN_TTL_MINUTES. Client should call /auth/refresh. |
| `AUTH_SESSION_REVOKED` | 401 | Session has been signed out | Device was signed out (logout, remote sign-out, password change or refresh-token reuse). |
| `AUTH_INVALID_CREDENTIALS` | 401 | Invalid username or password | Wrong username or password (unknown usernames give the same answer on purpose). |
| `AUTH_ACCOUNT_LOCKED` | 429 | Too many failed attempts. Try again later | Too many failed logins. `details.retryAfterSeconds` says when to retry. |
| `AUTH_REFRESH_INVALID` | 401 | Refresh token is invalid or expired | Refresh token unknown, expired or revoked; web clients also need the X-Chitbook-Client header. |
| `AUTH_REFRESH_REUSED` | 401 | Refresh token was already used; all sessions in this chain were signed out | An old refresh token was presented again; the whole session chain was revoked (possible theft). |
| `AUTH_WEAK_PASSWORD` | 422 | Password does not meet the password policy | Password under 8 chars, no letter+digit, too common, or equal to the username. |
| `AUTH_WRONG_CURRENT_PASSWORD` | 400 | Current password is incorrect | `currentPassword` does not match. |
| `AUTH_SESSION_NOT_FOUND` | 404 | Session not found | Session id not active for this user (already signed out?). |
| `ADMIN_REQUIRED` | 403 | Platform admin access is required | Only platform ADMIN users may call this. |
| `FORBIDDEN` | 403 | You do not have access to this resource | You may only access your own user data (unless platform ADMIN). |
| `NOT_GROUP_MEMBER` | 403 | You are not an active member of this group | Caller (or the target user) is not an ACTIVE member of the group. |
| `NOT_GROUP_ADMIN` | 403 | Group admin access is required | Caller is a member but not the group's ADMIN. |
| `USER_NOT_FOUND` | 404 | User not found | No user with that id/username. |
| `USERNAME_TAKEN` | 409 | Username is already taken | Username already registered (usernames are case-insensitive). |
| `EMAIL_TAKEN` | 409 | Email is already registered | Email already registered. |
| `CHIT_NOT_FOUND` | 404 | Chit not found | No chit with that id owned by the caller (other owners' chits look missing on purpose). |
| `CHIT_INVALID_INPUT` | 400 | Chit data is invalid | A chit rule failed; `message` names it (amount > 0, months 1-120, commission 0-20%, ...). |
| `CHIT_MEMBER_NOT_FOUND` | 400 | Member is not part of this chit | `memberId` belongs to another chit. |
| `CHIT_MONTH_OUT_OF_RANGE` | 400 | Month is outside the chit's duration | Month index outside 1..months. |
| `CHIT_PAYOUT_NOT_FOUND` | 404 | No payout recorded for this month | Nothing recorded for that month. |
| `GROUP_NOT_FOUND` | 404 | Chit group not found | Wrong group id or group code. |
| `GROUP_FULL` | 409 | Chit group has reached its member limit | Member count reached `totalMembers`. |
| `MEMBERSHIP_EXISTS` | 409 | User is already associated with this group | User already belongs to the group. |
| `MEMBERSHIP_PENDING` | 409 | A join request for this group is already pending | A join request is already waiting for approval. |
| `MEMBERSHIP_NOT_FOUND` | 404 | Membership not found | User is not in that group. |
| `PAYMENT_NOT_FOUND` | 404 | Payment not found | Wrong payment id. |
| `PAYMENT_MEMBER_INACTIVE` | 403 | Payments can only be recorded for active group members | The paying user is not an ACTIVE member. |
| `PAYMENT_NOT_ALLOWED` | 403 | You can only record payments for yourself unless you administer this group | Members may only record their own payments. |
| `PAYMENT_VERIFY_NOT_ALLOWED` | 403 | Only a group admin, accountant or platform admin can verify payments | Only group admins, ACCOUNTANT users or platform admins verify payments. |
| `FUND_NOT_FOUND` | 404 | Fund not found | Wrong fund id / group has no fund. |
| `LEDGER_NOT_FOUND` | 404 | Ledger entry not found | Wrong ledger entry id. |
| `AUCTION_NOT_FOUND` | 404 | Auction not found | Wrong auction id. |
| `AUCTION_EXISTS` | 409 | An auction already exists for this month in this group | The group already has an auction for that month. |
| `LOAN_NOT_FOUND` | 404 | Loan not found | No loan for that id / member. |
| `NOTIFICATION_NOT_FOUND` | 404 | Notification not found | Wrong notification id. |
| `NOTIFICATION_CONFIG_NOT_FOUND` | 404 | Notification config not found | Wrong config id. |
| `POLL_NOT_FOUND` | 404 | Poll not found | Wrong poll id. |
| `POLL_CLOSED` | 409 | Poll is closed | Poll closed or past `expiresAt`. |
| `POLL_OPTION_INVALID` | 400 | Option does not belong to this poll | Option belongs to another poll. |
| `POLL_ALREADY_VOTED` | 409 | You have already voted in this poll | One vote per user per poll. |
| `MEDIA_NOT_FOUND` | 404 | Media not found | Wrong media id. |
