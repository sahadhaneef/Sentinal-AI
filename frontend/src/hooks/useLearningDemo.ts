import { useId, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createLearningApi } from '../api/learningClient';
export function useLearningDemo() {
  const [api, setApi] = useState(createLearningApi),
    id = useId(),
    client = useQueryClient();
  const key = ['learning-demo', id, api];
  const query = useQuery({
    queryKey: ['learning-demo', id],
    queryFn: () => api.getIncident('inc_001'),
    staleTime: 0,
  });
  const mutation = useMutation({
    mutationFn: async (action: 'approve' | 'reject' | 'apply') => {
      const incident = (await api.getIncident('inc_001')).data,
        p = incident.patches[0],
        body = { candidate_id: p.id, patch_hash: p.patch_hash, base_revision: p.base_revision };
      if (action === 'apply') await api.applyApprovedPatch(incident.id, body);
      else await api.decide(incident.id, { ...body, decision: action });
    },
    onSettled: () => client.invalidateQueries({ queryKey: key.slice(0, 2) }),
  });
  const restart = async () => {
    const next = createLearningApi();
    setApi(next);
    client.setQueryData(['learning-demo', id], await next.getIncident('inc_001'));
  };
  return { query, mutation, restart };
}
