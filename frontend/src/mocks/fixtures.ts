import type {
  AgentDetail,
  Application,
  IncidentDetail,
  IncidentEvent,
  IncidentReport,
  RunState,
} from '../contracts/types';

const date = '2026-11-17T10:00:00Z';
export const makeReport = (id: string, outcome: RunState, generatedAt = date): IncidentReport => ({
  id: `report_${id}`,
  incident_id: id,
  version: 1,
  outcome,
  report_artifact_id: `art_report_${id}`,
  summary:
    outcome === 'resolved'
      ? 'Simulated reproduction and smoke checks passed after the approved local demo patch. No recurrence in one simulated observation cycle.'
      : outcome === 'unresolved'
        ? 'Simulated verification failed after application. The snapshot was restored; the incident remains unresolved.'
        : `Candidate ${outcome}. The demo workspace was not changed.`,
  limitations: [
    'Simulated evidence only; no code was executed.',
    'This result does not establish production recovery.',
  ],
  generated_at: generatedAt,
});
export function createFixtures() {
  const applications: Application[] = [
    {
      id: 'app_demo',
      name: 'Registration API',
      description:
        'The designated local sample application. A safe workspace for exploring the complete incident lifecycle.',
      workspace_key: 'local_registration_demo',
      repository_revision: 'abc123',
      monitoring_enabled: true,
      status: 'degraded',
      supported_errors: ['NullReferenceError', 'ValidationError'],
    },
  ];
  const states: RunState[] = [
    'awaiting_approval',
    'revision_requested',
    'manual_review',
    'rejected',
    'resolved',
    'awaiting_approval',
    'unresolved',
  ];
  const messages = [
    'Registration fails on missing profile',
    'Email validation regression',
    'Unrecognized worker log pattern',
    'Optional address fallback rejected',
    'Profile lookup recovered',
    'Candidate revision no longer matches',
    'Verification failed; sample restored',
  ];
  const incidents: IncidentDetail[] = states.map((status, index) => {
    const n = String(index + 1).padStart(3, '0'),
      id = `inc_${n}`,
      patchId = `patch_${n}`,
      hash = 'sha256:68bc2d7dd2b5854fc94d2c1935dbab100136aa193d3c8a0d5972fd5039ba3f27';
    const hasPatch = index !== 2;
    const patch: IncidentDetail['patches'][number] = {
      id: patchId,
      incident_id: id,
      run_id: `run_${n}`,
      version: 1,
      base_revision: 'abc123',
      patch_hash: hash,
      changed_files: ['src/registration.py'],
      rationale:
        'Guard a missing profile before reading its display name; keep existing behavior for complete profiles.',
      diff_artifact_id: `art_diff_${n}`,
      status:
        index === 1
          ? 'failed'
          : index === 3
            ? 'rejected'
            : index === 4 || index === 6
              ? 'applied'
              : 'validated',
      diff: '--- a/src/registration.py\n+++ b/src/registration.py\n@@ -42,2 +42,3 @@ def register_user(payload):\n-    name = payload["profile"]["name"]\n+    profile = payload.get("profile") or {}\n+    name = profile.get("name", "Guest")\n     return create_user(name)',
    };
    const checks = ['registration_reproduction', 'existing_profile_smoke'].map((name, i) => ({
      name,
      status: (index === 1 && i === 0 ? 'failed' : 'passed') as 'failed' | 'passed',
      exit_code: index === 1 && i === 0 ? 1 : 0,
      duration_ms: i ? 180 : 410,
      evidence_artifact_id: `art_test_${n}_${i}`,
      evidence:
        index === 1 && i === 0
          ? 'Simulated assertion failure: expected a valid email error.'
          : 'Simulated check completed with exit code 0.',
    }));
    return {
      id,
      application_id: 'app_demo',
      source_event_id: `event_${n}`,
      fingerprint: `registration_${n}`,
      severity: index === 2 ? 'medium' : index === 1 ? 'critical' : 'high',
      error_type:
        index === 2 ? 'UnsupportedLog' : index === 1 ? 'ValidationError' : 'NullReferenceError',
      message: messages[index],
      status,
      current_stage: status === 'revision_requested' ? 'repair' : status,
      repository_revision: 'abc123',
      active_run_id: `run_${n}`,
      detected_at: `2026-11-17T0${9 - index}:00:00Z`,
      resolved_at: index === 4 ? date : null,
      source_log:
        index === 2
          ? '[worker] unsupported signal 0x71 — context redacted'
          : '[registration] profile.name accessed on null profile\n  at src/registration.py:42 (personal data redacted)',
      diagnosis:
        index === 2
          ? null
          : {
              incident_id: id,
              run_id: `run_${n}`,
              status: 'completed',
              hypothesis:
                index === 1
                  ? 'Email validation fails on the reproduction fixture.'
                  : 'The registration handler accesses a profile before checking for a null value.',
              confidence_label: 'medium',
              uncertainty:
                'This hypothesis is limited to the designated sample and its supplied fixtures.',
              suggested_direction:
                'Add a minimal guard and preserve existing registration behavior.',
              evidence: [
                {
                  file_path: 'src/registration.py',
                  symbol: 'register_user',
                  start_line: 42,
                  end_line: 49,
                  repository_revision: 'abc123',
                  artifact_id: `art_code_${n}`,
                  excerpt: 'name = payload["profile"]["name"]',
                },
              ],
            },
      patches: hasPatch ? [patch] : [],
      validation: hasPatch
        ? {
            candidate_id: patchId,
            patch_hash: hash,
            status: index === 1 ? 'failed' : 'passed',
            checks,
            environment_id: `sandbox_${n}`,
            duration_ms: 590,
          }
        : null,
      decision:
        index === 3 || index === 4 || index === 6
          ? {
              id: `decision_${n}`,
              incident_id: id,
              candidate_id: patchId,
              patch_hash: hash,
              base_revision: 'abc123',
              decision: index === 3 ? 'reject' : 'approve',
              actor_id: 'demo_reviewer',
              comment: 'Seeded demonstration decision.',
              decided_at: date,
            }
          : null,
      application_attempt:
        index === 4 || index === 6
          ? {
              id: `attempt_${n}`,
              candidate_id: patchId,
              snapshot_ref: `simulated_snapshot_${n}`,
              before_revision: 'abc123',
              after_revision: index === 6 ? 'abc123' : 'demo789',
              status: index === 6 ? 'unresolved' : 'resolved',
              applied_at: date,
              restore_status: index === 6 ? 'restored' : 'not_needed',
            }
          : null,
      verification:
        index === 4 || index === 6
          ? {
              id: `verify_${n}`,
              application_attempt_id: `attempt_${n}`,
              candidate_id: patchId,
              status: index === 6 ? 'failed' : 'passed',
              checks:
                index === 6
                  ? checks.map((check, j) => ({
                      ...check,
                      status: j === 0 ? ('failed' as const) : check.status,
                      exit_code: j === 0 ? 1 : 0,
                      evidence:
                        j === 0
                          ? 'Simulated reproduction still fails after application.'
                          : check.evidence,
                    }))
                  : checks,
              monitoring_observation:
                index === 6
                  ? 'Supported error recurred during simulated verification. Snapshot restored; manual intervention required.'
                  : 'No supported error recurrence in one simulated observation cycle.',
              evidence_artifact_id: `art_verify_${n}`,
            }
          : null,
      report: index === 3 || index === 4 || index === 6 ? makeReport(id, status) : null,
      can_approve: index === 0 || index === 5,
      can_reject: index === 0 || index === 5,
      can_apply: false,
      permission_reason:
        index === 1
          ? 'Failed validation. A candidate revision is required (attempt 1 of 2).'
          : index === 2
            ? 'Needs manual review. No supported diagnosis or candidate.'
            : '',
    };
  });
  const agentInfo = [
    [
      'manager',
      'Manager Agent',
      'Delvin',
      'Coordinates the workflow and keeps every handoff accountable.',
      'Incident events, typed agent handoffs',
      'Stage dispatch, approval gates, audit events',
    ],
    [
      'monitoring',
      'Monitoring Agent',
      'Neha',
      'Spots supported failures in the designated sample application.',
      'Allowlisted sample logs',
      'Sanitized, deduplicated incident events',
    ],
    [
      'diagnosis',
      'Diagnosis Agent',
      'Sahad',
      'Connects errors to revision-bound code evidence with Code RAG.',
      'Error context, exact repository revision',
      'Cited hypothesis, uncertainty, suggested direction',
    ],
    [
      'repair',
      'Repair Agent',
      'Yadhulakshmi',
      'Proposes focused, reviewable patches with a clear rationale.',
      'Diagnosis evidence, source revision',
      'Immutable patch candidate, diff, hash',
    ],
    [
      'testing',
      'Testing Agent',
      'Sravan',
      'Validates candidates in isolation before human review.',
      'Exact patch candidate, reproduction fixture',
      'Check results, test evidence, verification',
    ],
    [
      'reporting',
      'Reporting Agent',
      'Neha',
      'Turns the incident journey into a clear, evidence-led report.',
      'Persisted decisions and verification results',
      'Outcome report, limitations, audit summary',
    ],
  ] as const;
  const agents: AgentDetail[] = agentInfo.map(
    ([agent_type, name, owner, responsibility, input, output]) => ({
      agent_type,
      name,
      owner,
      responsibility,
      status:
        agent_type === 'testing'
          ? 'error'
          : agent_type === 'diagnosis' || agent_type === 'reporting'
            ? 'completed'
            : 'idle',
      current_task: null,
      last_activity:
        agent_type === 'testing'
          ? 'Validation failed for inc_002; revision required.'
          : agent_type === 'manager'
            ? 'inc_001 is ready for human review.'
            : agent_type === 'reporting'
              ? 'Report generated for inc_005.'
              : 'Seeded sample execution completed.',
      inputs: input.split(', '),
      outputs: output.split(', '),
      recent_runs: [
        {
          schema_version: '1.0',
          incident_id: agent_type === 'testing' ? 'inc_002' : 'inc_001',
          run_id: agent_type === 'testing' ? 'run_002' : 'run_001',
          stage: agent_type,
          agent_type,
          status: agent_type === 'testing' ? 'error' : 'completed',
          created_at: date,
          input_revision: 'abc123',
          error: agent_type === 'testing' ? 'Reproduction assertion failed.' : null,
        },
      ],
    }),
  );
  const events: IncidentEvent[] = incidents.flatMap((i) => [
    {
      id: `evt_${i.id}_0`,
      incident_id: i.id,
      run_id: i.active_run_id!,
      event_type: 'detected',
      actor_type: 'agent' as const,
      actor_id: 'monitoring',
      payload: { message: 'Supported sample log received, or routed to manual review.' },
      occurred_at: i.detected_at,
    },
    {
      id: `evt_${i.id}_1`,
      incident_id: i.id,
      run_id: i.active_run_id!,
      event_type: i.status,
      actor_type: 'system' as const,
      actor_id: 'manager',
      payload: { message: i.permission_reason || 'Seeded workflow evidence available.' },
      occurred_at: date,
    },
  ]);
  return {
    applications,
    incidents,
    agents,
    events,
    settings: { monitoring_interval_seconds: 5, max_candidate_revisions: 2 },
  };
}
