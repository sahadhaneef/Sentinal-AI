# SENTINEL AI ? API Documentation

All endpoints are versioned under `/api/v1`.

## Canonical Envelopes

### Success Envelope
```json
{
  "data": { ... },
  "meta": {
    "request_id": "8bb38ce2-47d5-45cf-a4d3-066cb5bf705c",
    "schema_version": "1.0"
  }
}
```

### Error Envelope
```json
{
  "error": {
    "code": "CANDIDATE_STALE",
    "message": "Candidate revision does not match the demo workspace.",
    "details": {}
  },
  "meta": {
    "request_id": "8bb38ce2-47d5-45cf-a4d3-066cb5bf705c",
    "schema_version": "1.0"
  }
}
```

---

## Endpoint Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health and API version verification |
| `POST` | `/api/v1/auth/login` | Session login (sets session and CSRF cookie) |
| `POST` | `/api/v1/auth/logout` | Session logout (clears auth cookies) |
| `GET` | `/api/v1/auth/me` | Reviewer identity, permissions, and CSRF token |
| `GET` | `/api/v1/artifacts/{id}` | Retrieve sanitized artifact content (logs, diffs, evidence) |
| `GET` | `/api/v1/dashboard/summary` | Aggregate metrics, incident tallies, agent status list |
| `GET` | `/api/v1/applications` | List monitored applications |
| `GET` | `/api/v1/applications/{id}` | Application details, revision, and supported errors |
| `POST` | `/api/v1/applications/{id}/monitoring/start` | Enable monitoring for application |
| `POST` | `/api/v1/applications/{id}/monitoring/stop` | Stop monitoring for application |
| `GET` | `/api/v1/incidents` | List incidents with filters (`status`, `severity`, `application_id`, `scope`, `sort`, `search`, `cursor`, `limit`) |
| `POST` | `/api/v1/incidents` | Ingest incident event (with automatic fingerprint deduplication) |
| `GET` | `/api/v1/incidents/{id}` | Full incident detail including diagnosis, patches, validation, decision, verification, and action permissions |
| `GET` | `/api/v1/incidents/{id}/events` | Immutable append-only audit event timeline |
| `POST` | `/api/v1/incidents/{id}/runs` | Start a new workflow execution run |
| `GET` | `/api/v1/incidents/{id}/runs` | List workflow execution runs |
| `GET` | `/api/v1/incidents/{id}/diagnosis` | Root-cause hypothesis and citation evidence |
| `GET` | `/api/v1/incidents/{id}/patches` | Versioned patch candidates for the incident |
| `GET` | `/api/v1/incidents/{id}/report` | Final generated incident report |
| `GET` | `/api/v1/incidents/{id}/reports` | List all historical report versions |
| `GET` | `/api/v1/incidents/{id}/verification` | Post-patch verification test results |
| `POST` | `/api/v1/incidents/{id}/workflow/run-all` | Trigger full automated pipeline (diagnose -> repair -> test) |
| `GET` | `/api/v1/patches/{candidate_id}` | Detailed candidate information and diff |
| `GET` | `/api/v1/patches/{candidate_id}/validation` | Test checks and reproduction results for candidate |
| `POST` | `/api/v1/incidents/{id}/decision` | Human approval gate (`decision: "approve" \| "reject"`) |
| `POST` | `/api/v1/incidents/{id}/apply` | Controlled local patch application |
| `GET` | `/api/v1/agents` | Status summaries for all six agents |
| `GET` | `/api/v1/agents/{agent_type}` | Agent detail, inputs, outputs, and recent run history |
| `GET` | `/api/v1/settings` | Read allowlisted safe settings |
| `PATCH` | `/api/v1/settings` | Update safe settings (`monitoring_interval_seconds`, `max_candidate_revisions`) |

---

## Key Mutation Examples

### 1. Ingest Incident
```http
POST /api/v1/incidents
Content-Type: application/json

{
  "application_id": "app_demo",
  "source_event_id": "evt_101",
  "fingerprint": "reg_null_ptr_01",
  "severity": "high",
  "error_type": "NullReferenceError",
  "message": "Registration fails on missing profile",
  "source_log": "[registration] profile.name accessed on null profile at line 42",
  "repository_revision": "abc123"
}
```

### 2. Human Approval Decision
```http
POST /api/v1/incidents/inc_001/decision
Content-Type: application/json

{
  "candidate_id": "patch_001",
  "patch_hash": "sha256:68bc2d7dd2b5854fc94d2c1935dbab100136aa193d3c8a0d5972fd5039ba3f27",
  "base_revision": "abc123",
  "decision": "approve",
  "comment": "Verified exact diff and reproduction checks."
}
```

### 3. Controlled Patch Application
```http
POST /api/v1/incidents/inc_001/apply
Content-Type: application/json

{
  "candidate_id": "patch_001",
  "patch_hash": "sha256:68bc2d7dd2b5854fc94d2c1935dbab100136aa193d3c8a0d5972fd5039ba3f27",
  "base_revision": "abc123"
}
```

---

## Security & Idempotency Headers

### 1. CSRF Protection
Non-GET mutation requests (`POST`, `PATCH`, `PUT`, `DELETE`) require a CSRF token match:
- The server issues a cryptographically signed `csrf_token` cookie upon login or visiting `/api/v1/auth/me`.
- Clients must include this token in the `X-CSRF-Token` request header.
- Mismatched or missing CSRF tokens return `403 Forbidden` (`CSRF_MISMATCH`).

### 2. Mutation Idempotency
All mutating decision and application requests (`/decision`, `/apply`) support the `X-Idempotency-Key` header:
- Clients generate a unique UUID v4 string per intent.
- If a network interruption occurs, re-transmitting the request with the identical `X-Idempotency-Key` will return the cached response without re-executing state transitions or patch application.
- Duplicate executions with identical keys are prevented at the database level.

