// Thin fetch wrapper around the Spring Boot API (HTTP Basic auth).

export type Role = 'ADMIN' | 'MEMBER' | 'ACCOUNTANT';

export interface User {
  id: number;
  name: string;
  username: string;
  email: string;
  phone?: number;
  role: Role;
}

export interface Session {
  token: string; // base64 "username:password"
  user: User;
}

export interface ChitSummary {
  id: number;
  name: string;
  totalAmount: number;
  months: number;
  startMonth: string; // yyyy-MM
  memberCount: number;
  commissionPercent: number;
  monthsElapsed: number;
  dueToDate: number;
  collected: number;
  pending: number;
  overdue: number;
  payoutsDone: number;
  paidOut: number;
  profit: number;
  createdAt: string;
}

export interface ChitMember {
  id: number;
  name: string;
  shares: number;
  startMonth: string; // yyyy-MM, first month this member has an entry
  amounts: (number | null)[]; // index i = month i + 1
  paid: boolean[];
}

export interface Payout {
  month: number;
  memberId: number;
  memberName: string;
  amount: number;
  paidOn: string; // yyyy-MM-dd
}

export interface MonthSummary {
  month: number;
  calendarMonth: string;
  due: number;
  collected: number;
  pending: number;
  payout: number | null;
  pnl: number | null;
  isDue: boolean;
}

export interface Chit {
  id: number;
  name: string;
  totalAmount: number;
  months: number;
  startMonth: string;
  commissionPercent: number;
  perShareAmount: number;
  escalationEnabled: boolean;
  escalationPercent: number;
  members: ChitMember[];
  payouts: Payout[];
  monthSummaries: MonthSummary[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateChitMemberInput {
  name: string;
  shares: number;
  startMonth?: string; // yyyy-MM, defaults to the chit's own startMonth
}

export interface CreateChitInput {
  name: string;
  totalAmount: number;
  months: number;
  startMonth: string;
  perShareAmount?: number; // defaults to totalAmount / months when omitted
  members: CreateChitMemberInput[];
  commissionPercent: number;
  escalationEnabled?: boolean;
  escalationPercent?: number;
}

export interface AddMemberInput {
  name: string;
  shares: number;
  startMonth?: string;
}

export interface UpdateChitInput {
  totalAmount?: number;
  commissionPercent?: number;
  perShareAmount?: number;
  escalationEnabled?: boolean;
  escalationPercent?: number;
  entries?: { memberId: number; month: number; amount?: number; paid?: boolean }[];
}

export interface SavePayoutInput {
  memberId: number;
  amount: number;
  paidOn?: string;
}

export interface Stats {
  totals: {
    chits: number;
    dueToDate: number;
    collected: number;
    pending: number;
    overdue: number;
    paidOut: number;
    cashInHand: number;
    profit: number;
    expectedCommission: number;
    collectionRate: number | null;
  };
  monthly: { month: string; due: number; collected: number; payout: number; pnl: number; cumulativePnl: number }[];
  perChit: ChitSummary[];
  pendingDues: {
    chitId: number;
    chitName: string;
    memberId: number;
    memberName: string;
    month: number;
    calendarMonth: string;
    amount: number;
    overdue: boolean;
    daysOverdue: number;
  }[];
}

export interface SignupInput {
  name: string;
  username: string;
  email: string;
  phone?: number;
  password: string;
}

const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '';

const SESSION_KEY = 'chitbook.session';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function loadSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function saveSession(session: Session | null) {
  try {
    if (session) sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // storage unavailable (private mode); session lives in memory only
  }
}

// btoa only handles Latin-1, so encode as UTF-8 first
function toBase64(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  bytes.forEach((b) => (binary += String.fromCharCode(b)));
  return btoa(binary);
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set('Content-Type', 'application/json');
  const authToken = token ?? loadSession()?.token;
  if (authToken) headers.set('Authorization', `Basic ${authToken}`);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Is the backend running?');
  }

  if (res.status === 401 && !token && authToken) onUnauthorized();

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.message) message = body.message;
    } catch {
      // non-JSON error body
    }
    if (res.status === 401) message = 'Invalid username or password.';
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  async login(username: string, password: string): Promise<Session> {
    const token = toBase64(`${username}:${password}`);
    const user = await request<User>(
      '/api/chit/auth/login',
      { method: 'POST', body: JSON.stringify({ username, password }) },
      token,
    );
    return { token, user };
  },

  signup(input: SignupInput) {
    return request<User>('/api/chit/user/register', { method: 'POST', body: JSON.stringify(input) }, '');
  },

  listChits() {
    return request<ChitSummary[]>('/api/chit/simple-chits');
  },

  getChit(id: number) {
    return request<Chit>(`/api/chit/simple-chits/${id}`);
  },

  createChit(input: CreateChitInput) {
    return request<Chit>('/api/chit/simple-chits', { method: 'POST', body: JSON.stringify(input) });
  },

  addMember(id: number, input: AddMemberInput) {
    return request<Chit>(`/api/chit/simple-chits/${id}/members`, { method: 'POST', body: JSON.stringify(input) });
  },

  updateChit(id: number, input: UpdateChitInput) {
    return request<Chit>(`/api/chit/simple-chits/${id}`, { method: 'PUT', body: JSON.stringify(input) });
  },

  deleteChit(id: number) {
    return request<void>(`/api/chit/simple-chits/${id}`, { method: 'DELETE' });
  },

  savePayout(id: number, month: number, input: SavePayoutInput) {
    return request<Chit>(`/api/chit/simple-chits/${id}/payouts/${month}`, { method: 'PUT', body: JSON.stringify(input) });
  },

  deletePayout(id: number, month: number) {
    return request<Chit>(`/api/chit/simple-chits/${id}/payouts/${month}`, { method: 'DELETE' });
  },

  getStats() {
    return request<Stats>('/api/chit/simple-chits/stats');
  },
};
