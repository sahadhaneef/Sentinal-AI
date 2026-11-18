# ADR-002: incident-list query filters and boundary validation

Status: additive frontend contract clarification for the future FastAPI implementation.

The audit found that the history, open-incident and candidate queues filtered only a first page of at most 100 results, while the UI interpreted opaque cursors as numeric offsets. This could hide records and break production pagination.

`GET /incidents` retains its existing response and parameters, and adds two optional parameters:

- `scope`: `all` (default), `open`, `closed`, `candidates`, `pending`.
- `sort`: `detected_desc` (default), `detected_asc`, `severity_desc`.

Closed statuses are resolved, rejected, unresolved, reported. Open is the complement. Candidates selects incidents with at least one patch. Pending selects incidents with a patch in awaiting_approval, approved, applying, verifying or restoring. All filters intersect, including explicit status, severity, application and search. Filter and sort before paginating. Severity order: critical, high, medium, low. Use detected_at descending and then ID ascending as tie breakers (detected_asc uses ascending dates).

Both adapters accept these typed query fields. Existing clients omitting them retain their behavior. FastAPI must implement these optional fields before connecting the audited queue/history UI. No endpoint, response shape, required field, ID or status value changed. The browser never performs cursor arithmetic: it records visited opaque tokens in URL `from` parameters, which are UI-only and never sent to the API. Direct cursor links without a known trail offer forward navigation only.

Existing UTC timestamp requirements are now runtime-validated with ISO datetime schemas. Malformed local mutation/list-filter inputs use the same `VALIDATION_ERROR` 422 client error in both adapters. HTTP responses continue to be runtime-validated. Passing validation requires at least one recorded check, all checks passed with exit code zero, and matching candidate ID and patch hash.

Confirmation dialogs freeze the displayed candidate/hash/base, source revision, diff and validation evidence. Changed evidence blocks confirmation and requires fresh review. Mock apply additionally rechecks validation and current application revision. These checks demonstrate the contract; FastAPI must independently enforce authorization, revision matching, validation and approval.

A seventh optional fixture, `inc_007`, demonstrates failed post-apply verification, a restored snapshot and an unresolved report. The original six fixture IDs and scenarios are preserved. This adds no execution API or backend implementation.
