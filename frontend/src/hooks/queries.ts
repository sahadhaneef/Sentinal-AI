import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, demoControls, isDemo } from '../api/client';
import { readPreferences } from '../lib/preferences';
import { ApiClientError } from '../api/errors';
import type { AgentType, ApplyRequest, ApprovalRequest, IncidentFilters } from '../contracts/types';
export const terminalStates = [
  'resolved',
  'reported',
  'rejected',
  'unresolved',
  'manual_review',
  'error',
];
export const queryPolicy = {
  retry: (count: number, error: Error) =>
    count < 2 && (!(error instanceof ApiClientError) || error.status === 0 || error.status >= 500),
  retryDelay: (attempt: number) => Math.min(1000 * 2 ** attempt, 15000),
};
export const useDashboard = () =>
  useQuery({ queryKey: ['summary'], queryFn: () => api.getDashboardSummary() });
export const useHealth = () =>
  useQuery({
    queryKey: ['health'],
    queryFn: () => api.getHealth(),
    enabled: !isDemo,
    refetchInterval: 30000,
    refetchIntervalInBackground: false,
  });
export const useApplications = () =>
  useQuery({ queryKey: ['applications'], queryFn: () => api.listApplications() });
export const useApplication = (id: string) =>
  useQuery({ queryKey: ['application', id], queryFn: () => api.getApplication(id), enabled: !!id });
export const useIncidents = (filters: IncidentFilters = {}) =>
  useQuery({ queryKey: ['incidents', filters], queryFn: () => api.listIncidents(filters) });
export const useIncident = (id: string) =>
  useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.getIncident(id),
    refetchInterval: (q) => {
      if (q.state.error) return false;
      const d = q.state.data?.data;
      return d && !terminalStates.includes(d.status) ? Number(readPreferences().polling) : false;
    },
    refetchIntervalInBackground: false,
  });
export const useEvents = (id: string, active = false) =>
  useQuery({
    queryKey: ['events', id],
    queryFn: () => api.getIncidentEvents(id),
    refetchInterval: (query) => (active && !query.state.error ? 4000 : false),
    refetchIntervalInBackground: false,
  });
export const useAgents = () => useQuery({ queryKey: ['agents'], queryFn: () => api.listAgents() });
export const useAgent = (type: AgentType) =>
  useQuery({ queryKey: ['agent', type], queryFn: () => api.getAgent(type) });
export const useReport = (id: string) =>
  useQuery({ queryKey: ['report', id], queryFn: () => api.getReport(id) });
export const useBackendSettings = () =>
  useQuery({ queryKey: ['settings'], queryFn: () => api.getSettings() });
export function useResetDemo() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (!demoControls) throw new Error('Reset is available in demo mode only.');
      await demoControls.reset();
    },
    onSuccess: () => client.invalidateQueries(),
  });
}
export function useMonitoring(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => api.setMonitoring(id, enabled),
    onSuccess: () => client.invalidateQueries(),
  });
}
export function useWorkflowMutation(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (
      action: { type: 'decide'; body: ApprovalRequest } | { type: 'apply'; body: ApplyRequest },
    ) => {
      if (action.type === 'decide') await api.decide(id, action.body);
      else await api.applyApprovedPatch(id, action.body);
    },
    onSettled: () => client.invalidateQueries(),
  });
}
