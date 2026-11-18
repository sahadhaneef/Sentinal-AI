export const stages = [
  {
    name: 'Detect',
    agent: 'Monitoring Agent',
    description: 'Notice a supported error in the local sample before investigating it.',
    input: 'Sanitized sample application logs',
    output: 'An incident linked to the source revision',
    action: 'Open the incident and see what happened.',
  },
  {
    name: 'Diagnose',
    agent: 'Diagnosis Agent',
    description: 'Find a likely cause, grounded in the relevant source code.',
    input: 'Error context and revision-bound code evidence',
    output: 'A cited hypothesis with uncertainty clearly stated',
    action: 'Read the explanation and inspect the evidence.',
  },
  {
    name: 'Repair',
    agent: 'Repair Agent',
    description: 'Suggest a small change you can understand and review.',
    input: 'Diagnosis and the exact source revision',
    output: 'A versioned patch with an exact content hash',
    action: 'Compare the proposed change with the original.',
  },
  {
    name: 'Test',
    agent: 'Testing Agent',
    description: 'Evaluate the proposed change in an isolated environment.',
    input: 'The exact candidate and reproduction checks',
    output: 'Passed, failed or incomplete test evidence',
    action: 'Check the results. Failed tests block approval.',
  },
  {
    name: 'Approve',
    agent: 'Administrator: a human decision',
    description: 'You decide whether the exact proposal should proceed.',
    input: 'Candidate, source revision, diff and passing checks',
    output: 'An approval or rejection tied to this exact change',
    action: 'Approve or reject. Approval does not apply the patch.',
  },
  {
    name: 'Local apply',
    agent: 'Manager Agent, after separate confirmation',
    description: 'Apply only the exact approved change after a separate confirmation.',
    input: 'Exact approved candidate and a restorable snapshot',
    output: 'An application attempt ready for verification',
    action: 'Confirm local application separately. Approval alone does not apply a patch.',
  },
  {
    name: 'Verify',
    agent: 'Testing & Monitoring Agents',
    description: 'Check whether the applied change resolved the supported issue.',
    input: 'Application attempt and post-change checks',
    output: 'Verification evidence or an unresolved outcome',
    action: 'Inspect the recorded checks. Application alone does not establish recovery.',
  },
  {
    name: 'Report',
    agent: 'Reporting Agent',
    description: 'Keep an honest record of what happened and what remains uncertain.',
    input: 'Decisions, tests and verification evidence',
    output: 'An outcome report with clear limitations',
    action: 'Read the report and revisit the incident history.',
  },
];
export const team = [
  [
    'manager',
    'Manager Agent',
    'Keeps the whole process connected.',
    'Coordinates typed handoffs, retries, state transitions and approval gates.',
  ],
  [
    'monitoring',
    'Monitoring Agent',
    'Notices supported problems in sample logs.',
    'Sanitizes and deduplicates allowlisted log events.',
  ],
  [
    'diagnosis',
    'Diagnosis Agent',
    'Explains a likely cause with evidence.',
    'Uses Code RAG with file, line and exact revision citations.',
  ],
  [
    'repair',
    'Repair Agent',
    'Suggests a focused, reviewable change.',
    'Produces immutable versioned diffs tied to base revisions and hashes.',
  ],
  [
    'testing',
    'Testing Agent',
    'Checks changes before and after application.',
    'Records isolated reproduction, smoke checks and verification outcomes.',
  ],
  [
    'reporting',
    'Reporting Agent',
    'Makes outcomes easy to revisit.',
    'Builds reports from recorded facts, including missing evidence and failed recovery.',
  ],
] as const;
export const faq = [
  [
    'What is SENTINEL AI?',
    'A prototype workspace for understanding and reviewing application incidents. It demonstrates a supported local sample workflow with clearly labeled simulated data.',
  ],
  [
    'How do the six agents work together?',
    'The Manager coordinates Monitoring, Diagnosis, Repair, Testing and Reporting. Human approval is a separate gate, not another agent.',
  ],
  [
    'Does it automatically change my application?',
    'No. A proposal must pass validation and receive human approval. Applying it is a separate confirmed action. In the current demo, no real files are changed.',
  ],
  [
    'Is human approval required?',
    'Yes. Approval is linked to the exact candidate, patch hash and source revision. Changed evidence requires fresh review.',
  ],
  [
    'How can I try the prototype?',
    'Start the guided demo for a step-by-step simulation, or use onboarding to explore the existing sample workspace. No registration or login is required for demo mode.',
  ],
  [
    'Can I connect my own application?',
    'Not yet. The current prototype is scoped to one designated local sample. Arbitrary repositories and production deployments are not supported.',
  ],
  [
    'What happens if testing fails?',
    'Approval is blocked. The incident shows the failed checks and may require a candidate revision or manual review. Missing tests never count as success.',
  ],
  [
    'Can I review previous incidents?',
    'Yes. Incident History includes rejected, resolved and unresolved examples, with evidence and reports. Mock decisions last until a full reload or demo reset.',
  ],
];
