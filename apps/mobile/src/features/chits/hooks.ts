/** Server state for chits (TanStack Query). Screens use these hooks, never `api` directly. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/api/endpoints';
import type { AddMemberInput, Chit, CreateChitInput, SavePayoutInput, UpdateChitInput } from '@/api/types';

export const chitKeys = {
  all: ['chits'] as const,
  list: () => [...chitKeys.all, 'list'] as const,
  stats: () => [...chitKeys.all, 'stats'] as const,
  detail: (id: number) => [...chitKeys.all, 'detail', id] as const,
};

export const useChits = () => useQuery({ queryKey: chitKeys.list(), queryFn: api.listChits });
export const useStats = () => useQuery({ queryKey: chitKeys.stats(), queryFn: api.stats });
export const useChit = (id: number) =>
  useQuery({ queryKey: chitKeys.detail(id), queryFn: () => api.getChit(id), enabled: Number.isFinite(id) });

/** After any change: put the fresh chit in the cache and refetch lists/stats. */
function useChitMutation<V>(fn: (vars: V) => Promise<Chit>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (chit) => {
      qc.setQueryData(chitKeys.detail(chit.id), chit);
      void qc.invalidateQueries({ queryKey: chitKeys.list() });
      void qc.invalidateQueries({ queryKey: chitKeys.stats() });
    },
  });
}

export const useCreateChit = () => useChitMutation((input: CreateChitInput) => api.createChit(input));
export const useUpdateChit = (id: number) => useChitMutation((input: UpdateChitInput) => api.updateChit(id, input));
export const useAddMember = (id: number) => useChitMutation((input: AddMemberInput) => api.addMember(id, input));
export const useSavePayout = (id: number) =>
  useChitMutation(({ month, input }: { month: number; input: SavePayoutInput }) => api.savePayout(id, month, input));
export const useDeletePayout = (id: number) => useChitMutation((month: number) => api.deletePayout(id, month));

export function useDeleteChit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteChit(id),
    onSuccess: (_void, id) => {
      qc.removeQueries({ queryKey: chitKeys.detail(id) });
      void qc.invalidateQueries({ queryKey: chitKeys.all });
    },
  });
}
