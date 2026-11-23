# Diagnosis D0 audit and D1 architecture

Scope: Sahad's Diagnosis + Code RAG retrieval foundation only. Work remains on
`Diagno-Agent`; no commit, push, merge, rebase or change to `main` is authorized.
The 108 protected Phase 3 files still match their saved hashes. The remote branch
does not contain that unpublished foundation; publishing dependencies needs a
separate approved handoff.

## Actual repository findings

- `app/main.py` provides the Phase 3 FastAPI factory, DTO-backed reads and explicit
  operator intake. There is no implemented agent package, embedding provider or
  vector store. Existing `docs/CODE_RAG.md` is a historical boundary, not a working
  retrieval implementation.
- `app/models/application.py` already defines applications, immutable repository
  revisions, revision selection, artifact metadata and `CodeIndexEntry`. Revisions
  are portable opaque strings, not necessarily verifiable Git commit hashes.
- `app/models/diagnosis.py` defines Diagnosis and EvidenceReference. Composite FKs
  bind citations to application/revision; D1 will not create diagnosis conclusions
  or claim an agent execution occurred.
- `app/repositories/unit_of_work.py` owns commit/rollback and sanitized failures.
  `app/db/session.py` configures SQLite foreign keys and UTC/Unicode support.
  `app/db/types.py` provides validated IDs, relative keys and hashes.
- `app/services/artifacts.py` reads bounded, hash-checked files under the configured
  artifact root. The relational database stores references rather than source
  bodies. There is no existing artifact writer or embedding cache to duplicate.
- `app/core/config.py` permits only configured workspace keys beneath `demo_root`.
  Registration records operator-supplied revision/snapshot metadata; it does not
  cryptographically establish a Git worktree's revision.
- The frozen frontend evidence fields are relative path, symbol, lines, revision,
  artifact ID and excerpt. The proposed Manager request/response is not finalized.
  D1 must not change public DTOs, routes, states or frontend contracts.
- `pyproject.toml` targets Python 3.12 and Ruff's existing 100-character limit.
  Existing tests use isolated migrated SQLite databases and live local HTTP/browser
  probes. Historical counts must be verified on this branch, not assumed.

## Module boundaries and data flow

Implement `app/agents/diagnosis/code_rag/` as an injectable internal library:

1. A source catalog validates application/revision records, current configured
   workspace binding, allowed root and disjoint write destinations.
2. Ingestion reads a bounded, explicit source allowlist without executing code.
   Secrets, dependencies, generated files, links and unsafe paths are excluded.
3. Python AST boundaries provide function/class-aware chunks; bounded overlapping
   complete-line windows handle large definitions and documented language fallback.
4. An embedding protocol supports validated batched vectors. Production uses local
   CPU FastEmbed with `BAAI/bge-small-en-v1.5`, 384 dimensions; deterministic test
   embeddings exist only in tests. No silent semantic fallback is permitted.
5. A module-owned SQLAlchemy SQLite cache stores vectors, immutable scope seals
   and collection memberships. It is regenerable, local and ignored by Git, with
   no external vector server or changes to core Alembic migrations.
6. Indexing writes immutable source/manifest/excerpt artifacts and reuses existing
   Artifact/CodeIndexEntry records through the unit of work. Existing coordinates
   can be reused only after their actual bytes and metadata verify; conflicting
   records are never overwritten.
7. Hybrid retrieval combines cosine similarity with verified stack path/line or
   symbol membership. Evidence IDs resolve to real CodeIndexEntry records and
   stored source lines at that scope, not current mutable worktree contents.

## Revision, cache and transaction decisions

- Treat application/revision source content as immutable once sealed. A digest of
  the accepted source manifest detects modified/deleted files. Same-revision
  mutation is rejected; the operator/Manager must register a new revision. New
  revisions can reuse unchanged content embeddings, while old citations remain
  resolvable from immutable artifacts.
- Cache keys include embedding identity/dimensions and content hashes. Model and
  chunking profiles cannot silently reuse incompatible vectors or collections.
- A private index schema uses its own declarative metadata, never the shared
  domain Base. Explicit index creation may initialize that regenerable cache;
  importing the module or starting FastAPI must not create it or alter core tables.
- Core metadata and the private vector cache cannot share a normal SQL transaction.
  Reserve an immutable scope seal, prepare vectors/artifacts, commit verified core
  metadata, then atomically publish collection membership. Failed publication can
  leave harmless unreferenced metadata/cache entries; it must never expose a ready
  collection referring to uncommitted evidence. Retries are idempotent.
- Source bytes stay in approved artifact files, not ordinary vector-cache fields
  or logs. No write destination may overlap the indexed repository. No source,
  log, query or snippet is sent to a hosted embedding API.

## Dependencies and preservation

The semantic dependency is optional and isolated in a new Diagnosis requirements
lock; do not overwrite the protected `pyproject.toml`, `uv.lock` or core settings.
Pin FastEmbed and the downloaded model revision/files. Keep weights/indexes under
already ignored tooling/artifact directories. Load only local model files during
indexing/retrieval; downloads require an explicit setup action. Document actual
package/model versions, dimensions and real semantic smoke results in D1's report.

The default automated suite uses deterministic injected providers and synthetic
repositories, with separate explicit real-model verification. Provider failure,
missing indexes and missing/corrupt artifacts are reported honestly; exact-only
retrieval can be explicitly marked degraded, never labeled semantic success.

## Contract questions for Delvin before D2

1. Who freezes and registers a revision, and what proves that a configured worktree
   or snapshot belongs to it? D1's trust anchor is the operator's allowed revision
   binding plus its own immutable source manifest, not a claim of Git attestation.
2. Will Manager pass inline sanitized stack traces, artifact references, or both?
   D1 can expose an internal retrieval DTO without freezing a new public endpoint.
3. Confirm future Diagnosis uses existing `hypothesis`, `suggested_direction`,
   `completed`/`manual_review` fields; proposed `root_cause`/`suggested_fix` fields
   must not replace the frontend contract silently.
4. Confirm cancellation, time limits, authorization, audit ownership, and whether
   partial/exact-only retrieval should lead to manual review in D2.
5. Who owns retention of immutable source artifacts, referenced code entries and
   old-revision vector collections? D1 must not prune evidence used by others.

## Implementation and validation plan

Verify the current 153-test foundation first. Add typed configuration/contracts,
safe ingestion, chunking, embedding validation/local provider, private vector
cache, artifact/catalog integration and hybrid retrieval incrementally. Add
synthetic ingestion/chunking/provider/index/retrieval/isolation tests, run the full
backend suite and unchanged migration/contract checks, and run a real local-model
retrieval smoke test separately. No LLM reasoning, other agents, repair, execution,
public API changes or D2 implementation are included. Stop before commit/push.
