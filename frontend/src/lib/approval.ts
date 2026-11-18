import type { IncidentDetail, PatchCandidate, ValidationResult } from '../contracts/types';

export function hasPassingValidation(patch: PatchCandidate, validation: ValidationResult | null) {
  return (
    !!validation &&
    validation.candidate_id === patch.id &&
    validation.patch_hash === patch.patch_hash &&
    validation.status === 'passed' &&
    validation.checks.length > 0 &&
    validation.checks.every((c) => c.status === 'passed' && c.exit_code === 0)
  );
}
export function reviewAccess(incident: IncidentDetail) {
  const patch = incident.patches.at(-1);
  const current =
    !!patch && patch.base_revision === incident.repository_revision && patch.status !== 'stale';
  const passed = !!patch && hasPassingValidation(patch, incident.validation);
  const decision = incident.decision;
  const approved =
    !!patch &&
    decision?.decision === 'approve' &&
    decision.incident_id === incident.id &&
    decision.candidate_id === patch.id &&
    decision.patch_hash === patch.patch_hash &&
    decision.base_revision === patch.base_revision;
  return {
    canApprove:
      incident.can_approve && current && passed && incident.status === 'awaiting_approval',
    canReject: incident.can_reject && current && incident.status === 'awaiting_approval',
    canApply: incident.can_apply && current && passed && approved && incident.status === 'approved',
    reason:
      incident.permission_reason ||
      (!patch
        ? 'No candidate is available.'
        : !current
          ? 'Candidate revision changed. Fresh review is required.'
          : !passed
            ? 'Passing validation for this exact candidate is required.'
            : ''),
  };
}
