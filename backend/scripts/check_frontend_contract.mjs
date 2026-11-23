// Runs the unchanged TypeScript HTTP adapter and Zod against actual FastAPI HTTP responses.
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { build } from "../../frontend/node_modules/vite/dist/node/index.js";

const base = process.argv[2];
if (!base || !/^http:\/\/(127\.0\.0\.1|localhost):\d+\/api\/v1$/.test(base)) {
  throw new Error(
    "Supply an exact local API base, e.g. http://127.0.0.1:8000/api/v1",
  );
}
const result = await build({
  configFile: false,
  root: fileURLToPath(new URL("../../frontend/", import.meta.url)),
  logLevel: "error",
  build: {
    write: false,
    lib: {
      entry: fileURLToPath(
        new URL("../../frontend/src/api/realAdapter.ts", import.meta.url),
      ),
      formats: ["es"],
    },
    minify: false,
  },
});
const output = (Array.isArray(result) ? result[0] : result).output;
const chunk = output.find((item) => item.type === "chunk" && item.isEntry);
assert.ok(chunk);
const { HttpSentinelApi } = await import(
  `data:text/javascript;base64,${Buffer.from(chunk.code).toString("base64")}`
);
globalThis.document = { cookie: "" }; // No browser session or fake identity is established.
const api = new HttpSentinelApi(base);
const resultHealth = await api.getHealth();
assert.equal(resultHealth.data.status, "ok");
assert.equal(resultHealth.meta.schema_version, "1.0");
assert.match(resultHealth.meta.request_id, /^[0-9a-f-]{36}$/);
if (process.argv[3] === "persisted") {
  const applications = (await api.listApplications()).data;
  assert.equal(applications.length, 1);
  assert.equal(
    (await api.getApplication(applications[0].id)).data.repository_revision,
    "demoabc",
  );
  const page = (
    await api.listIncidents({ scope: "closed", sort: "detected_asc" })
  ).data;
  assert.equal(page.total, 1);
  const id = page.items[0].id;
  const detail = (await api.getIncident(id)).data;
  assert.equal(detail.report.outcome, "unresolved");
  assert.equal(detail.can_approve, false);
  assert.equal(detail.can_apply, false);
  assert.equal(detail.patches[0].id, "patch_001");
  assert.ok(detail.patches[0].diff.includes("+new"));
  assert.equal((await api.getIncidentEvents(id)).data.length, 1);
  assert.equal((await api.listPatches(id)).data.length, 1);
  assert.equal((await api.getPatch("patch_001")).data.id, "patch_001");
  assert.equal((await api.getValidation("patch_001")).data.status, "passed");
  assert.equal((await api.getReport(id)).data.outcome, "unresolved");
  assert.equal((await api.getDashboardSummary()).data.total_incidents, 1);
  for (const agent of (await api.listAgents()).data) {
    assert.equal(
      (await api.getAgent(agent.agent_type)).data.recent_runs.length,
      1,
    );
  }
  assert.equal((await api.getSettings()).data.monitoring_interval_seconds, 5);
  await assert.rejects(
    api.getPatch("missing"),
    (error) => error.status === 404,
  );
  await assert.rejects(
    api.listIncidents({ cursor: "invalid" }),
    (error) => error.status === 422,
  );
  await assert.rejects(
    api.applyApprovedPatch(id, {
      candidate_id: "patch_001",
      patch_hash: detail.patches[0].patch_hash,
      base_revision: "demoabc",
    }),
    (error) => error.status === 501,
  );
  console.log(
    JSON.stringify({
      persisted_reads: "passed",
      nested_Zod_projections: "passed",
      transport: "real HTTP adapter to FastAPI",
    }),
  );
  process.exit(0);
}
assert.deepEqual((await api.listApplications()).data, []);
assert.deepEqual((await api.listIncidents()).data, {
  items: [],
  total: 0,
  next_cursor: null,
});
assert.equal((await api.getDashboardSummary()).data.total_incidents, 0);
assert.equal((await api.listAgents()).data.length, 6);
for (const agent of (await api.listAgents()).data) {
  assert.equal(agent.status, "idle");
  assert.deepEqual((await api.getAgent(agent.agent_type)).data.recent_runs, []);
}
await api.getSettings();
await assert.rejects(
  api.getApplication("missing"),
  (error) => error.status === 404 && error.code === "NOT_FOUND",
);
await assert.rejects(
  api.decide("missing", {
    candidate_id: "missing",
    patch_hash: "opaque",
    base_revision: "opaque",
    decision: "approve",
  }),
  (error) => error.status === 501 && error.code === "NOT_IMPLEMENTED",
);
console.log(
  JSON.stringify({
    health: "passed",
    error_envelope: "passed",
    empty_reads: "passed",
    unavailable_mutations: "passed",
    transport: "real HTTP adapter to FastAPI",
    scope: "Phase 3 empty database",
  }),
);
