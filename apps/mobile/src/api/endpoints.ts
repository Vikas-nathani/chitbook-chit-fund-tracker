/** One function per API endpoint the app uses. Routes are documented in docs/api/. */
import { CLIENT_TYPE, DEVICE_NAME } from '@/lib/config';

import { json, request } from './client';
import type {
  AddMemberInput,
  Chit,
  ChitStats,
  ChitSummary,
  CreateChitInput,
  DeviceSession,
  SavePayoutInput,
  SignupInput,
  TokenResponse,
  UpdateChitInput,
  User,
} from './types';

const V1 = '/api/v1';

export const api = {
  // auth
  login: (username: string, password: string) =>
    request<TokenResponse>(
      `${V1}/auth/login`,
      { method: 'POST', ...json({ username, password, deviceName: DEVICE_NAME, client: CLIENT_TYPE }) },
      false,
    ),
  register: (input: SignupInput) =>
    request<User>(`${V1}/auth/register`, { method: 'POST', ...json(input) }, false),
  logout: () => request<void>(`${V1}/auth/logout`, { method: 'POST' }),
  me: () => request<User>(`${V1}/auth/me`),
  sessions: () => request<DeviceSession[]>(`${V1}/auth/sessions`),
  revokeSession: (id: string) => request<void>(`${V1}/auth/sessions/${id}`, { method: 'DELETE' }),

  // simple chits
  listChits: () => request<ChitSummary[]>(`${V1}/simple-chits`),
  stats: () => request<ChitStats>(`${V1}/simple-chits/stats`),
  getChit: (id: number) => request<Chit>(`${V1}/simple-chits/${id}`),
  createChit: (input: CreateChitInput) =>
    request<Chit>(`${V1}/simple-chits`, { method: 'POST', ...json(input) }),
  updateChit: (id: number, input: UpdateChitInput) =>
    request<Chit>(`${V1}/simple-chits/${id}`, { method: 'PATCH', ...json(input) }),
  deleteChit: (id: number) => request<void>(`${V1}/simple-chits/${id}`, { method: 'DELETE' }),
  addMember: (id: number, input: AddMemberInput) =>
    request<Chit>(`${V1}/simple-chits/${id}/members`, { method: 'POST', ...json(input) }),
  savePayout: (id: number, month: number, input: SavePayoutInput) =>
    request<Chit>(`${V1}/simple-chits/${id}/payouts/${month}`, { method: 'PUT', ...json(input) }),
  deletePayout: (id: number, month: number) =>
    request<Chit>(`${V1}/simple-chits/${id}/payouts/${month}`, { method: 'DELETE' }),
};
