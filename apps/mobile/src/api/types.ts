/** Friendly names for the generated API types (src/api/schema.d.ts, see scripts/gen-api-types.sh). */
import type { components } from './schema';

type S = components['schemas'];

export type User = S['UserOut'];
export type TokenResponse = S['TokenResponse'];
export type DeviceSession = S['SessionOut'];

export type ChitSummary = S['SimpleChitSummaryOut'];
export type Chit = S['SimpleChitOut'];
export type ChitMember = S['MemberOut'];
export type Payout = S['PayoutOut'];
export type MonthSummary = S['MonthSummaryOut'];
export type ChitStats = S['SimpleChitStats'];
export type PendingDue = S['PendingDue'];
export type StatsMonthPoint = S['StatsMonthPoint'];

export type CreateChitInput = S['SimpleChitCreate'];
export type CreateChitMemberInput = S['MemberInput'];
export type UpdateChitInput = S['SimpleChitUpdate'];
export type SavePayoutInput = S['SavePayout'];
export type AddMemberInput = S['AddMember'];

export interface SignupInput {
  name: string;
  username: string;
  email: string;
  phone?: string;
  password: string;
}

/** Every API error has this shape (docs/api/README.md). */
export interface ApiErrorBody {
  error: { code: string; message: string; details: unknown; requestId: string | null };
}
