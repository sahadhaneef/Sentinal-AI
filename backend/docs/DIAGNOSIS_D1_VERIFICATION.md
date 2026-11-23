# Diagnosis + Code RAG: D0/D1 verification

Verified on 2026-11-23 with Python 3.12.16, Windows x64, on branch
`Diagno-Agent`. This milestone implements internal source-evidence retrieval.
It does not implement a Diagnosis LLM, Manager orchestration, other agents,
patch generation/application, new public routes, or frontend changes.

## Architecture and preservation

The pre-implementation audit and decisions are in
`DIAGNOSIS_D0_ARCHITECTURE.md`. Phase 3 remains the integration foundation.

The callable entry point is `app.agents.diagnosis.code_rag.service.CodeRag`:

1. Resolve registered application/revision and operator permission.
2. Capture and filter bounded source bytes without executing/importing them.
3. Split Python definitions or complete-line fallback windows.
4. Seal the source manifest, reuse cached vectors, and embed missing content.
5. Verify source did not change during embedding.
6. Commit immutable source artifacts and `CodeIndexEntry` records together.
7. Atomically publish the scoped private vector collection.
8. Retrieve by local semantic similarity and verified stack frames, resolving
   every returned citation against the stored full source and excerpt bytes.

Reused infrastructure: `Settings`/`DemoWorkspace`, `Application`,
`RepositoryRevision`, `ApplicationRevision`, `Artifact`, `CodeIndexEntry`,
incident/event/run linkage, the existing `Evidence` DTO, `transaction`/`Store`,
SQLite engine configuration, relative-key/token validation, artifact confinement,
secret redaction, and the existing Alembic migrations. D1 does not write diagnoses,
evidence-reference conclusions, agent executions, or workflow transitions.

No existing source/configuration/test/migration file was modified for D1.
All 108 files in the Phase 3 preservation manifest retain their recorded SHA-256
hashes. Root instructions and branch restrictions remain in force. Existing dirty
frontend files and untracked Phase 3 backend files were present before this work.

## Files created

All paths below are relative to `backend/`:

| File | Responsibility |
| --- | --- |
| `app/agents/__init__.py` | Agent package boundary; no worker startup |
| `app/agents/diagnosis/__init__.py` | Diagnosis ownership boundary |
| `app/agents/diagnosis/code_rag/__init__.py` | Internal retrieval package |
| `app/agents/diagnosis/code_rag/config.py` | Independent optional RAG settings |
| `app/agents/diagnosis/code_rag/contracts.py` | Typed scope, chunks, requests and evidence |
| `app/agents/diagnosis/code_rag/errors.py` | Sanitized internal error codes |
| `app/agents/diagnosis/code_rag/hashing.py` | Canonical hashes and stable UUID5 identities |
| `app/agents/diagnosis/code_rag/catalog.py` | Domain scope, permission and storage separation |
| `app/agents/diagnosis/code_rag/ingestion.py` | Bounded safe source filtering and capture |
| `app/agents/diagnosis/code_rag/chunking.py` | Python AST and overlapping line windows |
| `app/agents/diagnosis/code_rag/embeddings.py` | Provider protocol, validation, real CPU encoder |
| `app/agents/diagnosis/code_rag/setup_model.py` | Explicit pinned public model download |
| `app/agents/diagnosis/code_rag/cache.py` | Private SQLite repositories and transactions |
| `app/agents/diagnosis/code_rag/evidence_store.py` | Shared artifacts/citations and resolution |
| `app/agents/diagnosis/code_rag/stacktrace.py` | Safe stack-frame parsing and matching |
| `app/agents/diagnosis/code_rag/service.py` | Indexing and hybrid retrieval facade |
| `app/agents/diagnosis/code_rag/verify_semantic.py` | Disposable real-model verification command |
| `tests/diagnosis/__init__.py`, `conftest.py` | Isolated migrated fixture and test-only encoder |
| `tests/diagnosis/test_ingestion.py` | Filtering, limits, real junction/hardlink rejection |
| `tests/diagnosis/test_chunking.py` | Syntax boundaries, ranges, overlaps, stable IDs |
| `tests/diagnosis/test_embeddings.py` | Malformed vectors, normalization and failures |
| `tests/diagnosis/test_index_retrieval.py` | Persistence, caching, isolation, rollback, citations |
| `tests/diagnosis/test_context.py` | Incident/log/run linkage and concurrent source change |
| `requirements-diagnosis.in`, `requirements-diagnosis.lock` | Optional hashed semantic dependencies |
| `docs/DIAGNOSIS_D0_ARCHITECTURE.md` | Audit and architecture before implementation |
| `docs/DIAGNOSIS_D1_VERIFICATION.md` | This report and setup/handoff guide |

Model weights, private indexes, temporary databases, environment packages and
local preservation files are ignored/generated data, not source deliverables.
No shared Alembic migration is needed: the domain schema is unchanged.

## Local semantic model

- Runtime: FastEmbed **0.9.1**, CPU ONNX Runtime **1.32.0** on this machine.
- Model: **BAAI/bge-small-en-v1.5**, English, MIT license.
- Quantized repository: `Qdrant/bge-small-en-v1.5-onnx-Q`.
- Immutable repository revision: `aa8f8b060edb00e03bfdd08813a2949946c8ba55`.
- Dimensions: **384**, L2-normalized for cosine ranking; maximum 512 tokenizer
  tokens. Query and document inputs use the same raw-text encoder preprocessing.
- ONNX file: `model_optimized.onnx`, 66,465,124 bytes,
  SHA-256 `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431`.
- The pinned tokenizer/config Git blob checksums and ONNX SHA-256 are in
  `embeddings.py`. Runtime checks those files before native model loading.
- Default batch size 16 and two CPU threads; no GPU, paid service, API key, hosted
  embeddings, or source uploads. Loading is lazy and `local_files_only=True`.
- Missing/corrupt weights or provider failures never select a synthetic fallback.
  The deterministic vocabulary encoder exists only under `tests/diagnosis/`.

The optional lock installed 20 additional packages without replacing any existing
core environment version. `pyproject.toml` and `uv.lock` were preserved. Install
the optional lock after syncing the core environment; a later exact `uv sync`
may remove these optional packages.

References: [FastEmbed documentation](https://qdrant.tech/documentation/embeddings/fastembed/),
[supported models](https://qdrant.github.io/fastembed/examples/Supported_Models/),
[pinned model files](https://huggingface.co/Qdrant/bge-small-en-v1.5-onnx-Q/tree/aa8f8b060edb00e03bfdd08813a2949946c8ba55).

## Setup and invocation

From `D:\projects\SENTINAL AI\backend`, use the existing Python 3.12 environment.
After the normal core setup described in the backend README:

```powershell
# The repository's existing uv executable; no core dependency lock changes.
& '..\.tools\uv\uv.exe' pip install --python '.venv/Scripts/python.exe' --require-hashes -r requirements-diagnosis.lock

# Explicit network operation: fixed public model files only, no repository upload.
& '.venv/Scripts/python.exe' -m app.agents.diagnosis.code_rag.setup_model

# Real local encoder, fresh Alembic database, synthetic sources and private index.
& '.venv/Scripts/python.exe' -m app.agents.diagnosis.code_rag.verify_semantic

# Offline automated tests use injected test providers, never live LLM calls.
& '.venv/Scripts/python.exe' -m ruff check .
& '.venv/Scripts/python.exe' -m ruff format --check .
& '.venv/Scripts/python.exe' -m pytest
```

Model setup is idempotent for valid installed files. An interrupted download may
leave a `<filename>.download` staging file: inspect/remove that specific partial
file before retrying. Invalid existing weights fail checksum verification and
must be explicitly repaired; runtime does not replace them silently.

`RagSettings` accepts `SENTINEL_RAG_` environment variables and deliberately reads
no dotenv file. Do not add these variables to the shared backend `.env`, whose
existing strict parser is unchanged. Defaults:

| Setting suffix | Default |
| --- | --- |
| `INDEX_ROOT` | `backend/artifacts/code-rag-index` |
| `MODEL_ROOT` | repository `.tools/code-rag-models/bge-small-en-v1.5` |
| `MAX_FILE_BYTES`, `MAX_TOTAL_BYTES` | 131072, 2097152 |
| `MAX_FILES`, `MAX_ENTRIES`, `MAX_DEPTH`, `MAX_CHUNKS` | 256, 4096, 24, 2000 |
| `MAX_CHUNK_LINES`, `MAX_CHUNK_CHARS`, `OVERLAP_LINES` | 48, 1600, 4 |
| `EMBEDDING_BATCH_SIZE`, `EMBEDDING_THREADS` | 16, 2 |
| `MIN_SEMANTIC_SCORE` | 0.25 cosine threshold |

Source ingestion additionally requires existing operator `permitted_workspaces`
configuration and domain application/revision/selection records. Only
`demo_root / application.workspace_key` at the operator's current allowed revision
can be indexed. There is no arbitrary path/remote-clone argument. Existing Phase 3
intake owns registration; this module does not invent registration APIs.

Internal integration example, with existing registered application/revision:

```python
from app.agents.diagnosis.code_rag.contracts import RetrievalRequest
from app.agents.diagnosis.code_rag.service import CodeRag
from app.core.config import Settings
from app.db.session import create_database_engine

settings = Settings()
engine = create_database_engine(settings)
try:
    rag = CodeRag(engine, settings)
    index_report = rag.index("existing_application_id", "registered_revision")
    result = rag.retrieve(
        RetrievalRequest(
            application_id="existing_application_id",
            repository_revision="registered_revision",
            error_type="KeyError",
            error_message="name missing during registration",
            stack_trace='File "registration.py", line 3, in register_user',
            top_k=5,
        )
    )
finally:
    engine.dispose()
```

`index` raises typed source/provider/index or existing persistence errors on
failure. `retrieve` returns `ready`, `empty`, `partial` or `unavailable`, a stable
reason code and verified evidence. Neither operation changes workflow state.
Input Pydantic validation rejects empty queries, invalid identifiers/revisions,
unbounded top-k, and a run without an incident. Do not bypass validation using
Pydantic `model_construct`/unchecked copies with external input.

## Ingestion and chunking behavior

Accepted extensions are an explicit configurable subset of Python, JS/JSX,
TS/TSX, Java, Go, Rust, C/header and C++/header. Hidden paths, dependencies,
build/generated outputs, credentials and sensitive configuration filenames are
excluded. Direct file reads enforce the same path/type restrictions. Potential
credential assignments/tokens/PEM content, NUL/binary input, invalid UTF-8,
oversized files and hardlinks are excluded with reason counts. Unreadable input
fails the scan safely. Total accepted bytes/files and visited entries/depth are
bounded; redirected roots/storage and traversal are rejected.

Python AST partitioning preserves decorated functions, classes/methods and module
gaps. Nested functions retain their enclosing function's context. Large spans
use bounded overlapping complete-line windows. Other languages and malformed
Python use the documented complete-line fallback, with no symbol invented.
A single line exceeding the character limit fails indexing rather than silently
truncating its citation. Blank files produce no chunks. UTF-8 bytes and CRLF/LF
are preserved; line coordinates are one-based and inclusive.

Sources/logs are data, never instructions. No ingested code is executed, imported,
written to, or passed to an LLM. Secret scanning is conservative pattern matching,
not a complete DLP system; only operator-reviewed local demo sources are supported.

## Index, revisions and evidence

`vectors-v1.sqlite3` uses its own SQLAlchemy declarative base and three private
tables: immutable source seals, normalized float32 vectors with checksums, and
profile-scoped collections with memberships embedded as bounded JSON
(`rag_source_seals_v1`, `rag_vectors_v1`, `rag_collections_v1`). An incompatible
existing database is rejected unchanged. No import or FastAPI startup creates it.

This simple brute-force cosine index avoids an external server and is suitable
for the bounded prototype. It is not an ANN service or a large-repository index.
Vector keys cover content hash, provider profile and dimensions; collection keys
add application, revision and chunking profile. Duplicate/unchanged text can
reuse vectors across revisions/applications, but collection memberships and
citations are always scoped. Reported cached/embedded counts count unique texts.

Accepted file path/hash manifests are immutable per application/revision.
Modification, addition or deletion under an already sealed revision requires a
new registered revision. New revisions reuse unchanged embeddings and omit deleted
files. Old citations resolve to immutable approved artifact files, independently
of current worktree edits. Even if the private cache is lost, the main stored
manifest prevents silently replacing an existing revision during rebuilding.

Artifacts contain full filtered source files, a manifest, and bounded excerpts;
ordinary database fields contain references/hashes/metadata only. Full snapshots
are not marked publicly displayable. Existing citation coordinates are reused
only if the symbol, hash and actual excerpt verify. Conflicts roll back the main
transaction. Private collection publication occurs only after domain commit.
Cross-database failures may leave unreferenced immutable blobs/domain rows; safe
retry is supported, destructive garbage collection is intentionally absent.

## Retrieval and ranking

Stack parsing supports Python file/line/symbol frames and file:line[:column]
frames for the supported common languages. A path must exactly match an indexed
relative path or have one unique full relative-path suffix. Ambiguous paths,
traversal and URLs are ignored. Absolute trace paths are never opened or exposed
as evidence. An optional log artifact must already be linked through monitoring
events/incidents to the requested application/revision and pass the existing
bounded redacted-log reader. Optional incident/run identities are scope checked.

Ranking uses cosine similarity `c` and verified exact tier `t`:

```text
t = 2: path and source line are inside the actual stored chunk
t = 1: verified path and symbol, without a matching line range
t = 0: semantic-only candidate
score = 0.4 * t + 0.2 * ((c + 1) / 2)
```

When semantics are unavailable, the semantic contribution is zero and only
verified exact candidates can be returned, explicitly `partial` and
`semantic_used=false`. Missing evidence returns an empty list. Semantic-only
candidates must meet the configured cosine threshold. Sorting is deterministic;
top-k is 1–20. A retrieval score is not a root-cause confidence probability.

Every returned item rechecks the domain scope, immutable manifest, artifact
hashes, full file hash, exact line slice and bounded excerpt. Broken citations are
excluded and the result is marked degraded. No LLM invents paths/IDs/ranges.

## Real-model results

The explicit semantic command ran successfully with the actual pinned ONNX model,
not the deterministic test encoder. It migrated an isolated temporary database,
passed Alembic schema comparison, indexed three synthetic files into three chunks,
excluded `.env`, and embedded three texts. Identical reindexing embedded zero and
reused all three vectors. A fresh service instance reloaded persisted vectors and
the local model and returned the same evidence ID.

For “A new user cannot sign up because a missing name field is accessed directly,”
semantic-only ranking was:

| Rank | File | Cosine |
| --- | --- | --- |
| 1 | `registration.py` | 0.681580 |
| 2 | `billing.py` | 0.531233 |
| 3 | `storage.py` | 0.413753 |

Adding an exact `billing.py:3` frame correctly put the billing citation first,
with hybrid score 0.969776 and exact tier 2. These are smoke results, not a
production retrieval-quality benchmark. The low prototype threshold admits
secondary candidates; calibrate it on representative incidents before D2.

Example actual top semantic citation (excerpt shortened here for readability):

```json
{
  "evidence_id": "0076bffe-11ac-535c-a666-197fbb2ab4d9",
  "application_id": "smoke_app",
  "repository_revision": "smoke-r1",
  "file_path": "registration.py",
  "symbol": "register_user",
  "start_line": 1,
  "end_line": 4,
  "artifact_id": "554d67d6-a149-558d-b6c0-fa1ca8b213e0",
  "source_snapshot_ref": "8993eb91-47df-57ff-bc46-08448008a23a",
  "source_file_ref": "da051328-6d7e-5785-875e-1a8d4cfdeea8",
  "content_hash": "sha256:f03b65a1e0e49a155ac2bef49dbf63fada0859ba32a4eaeeacff1394e6506538",
  "retrieval_method": "semantic",
  "rank": 1,
  "score": 0.1681579603777848,
  "semantic_score": 0.681579603777848,
  "exact_tier": 0
}
```

The smoke databases/artifacts are temporary and removed at command completion;
the reusable source citations above describe that verification run, not records
inserted into the real application database.

## Actual validation

| Check | Result |
| --- | --- |
| `python -m ruff check .` | Passed, no suppressions added |
| `python -m ruff format --check .` | Passed, 113 files already formatted, including the new documentation code example |
| `python -m pytest tests/diagnosis -q` | Final focused rerun: 56 passed in 7.84 seconds; real Windows junction/hardlink checks included |
| `python -m pytest` | 209 passed in 73.55 seconds; no failures/skips |
| Real `verify_semantic` command | Passed; actual local 384-dimensional embeddings |
| Fresh migration + Alembic check | Passed in smoke and existing migration tests; no schema drift |
| Preservation hashes | All 108 protected files unchanged |
| Existing local database | Read-only logical SHA-256 comparison matches the preservation backup |
| `uv pip check` | All 52 installed packages compatible; existing core versions preserved |
| Branch/reference/staging checks | `Diagno-Agent`; refs unchanged; nothing staged/committed/pushed |

The initial pre-implementation baseline had 151 passes and two native Node
process aborts in existing live frontend probes (exit 3221226505). The focused
four-probe rerun passed; the full final 209-test run also passed without changing
those tests. An early restricted filesystem test invocation could not create
native links; rerunning with native filesystem permissions passed actual link
safety checks without skips. New test fixture newline expectations were corrected
to distinguish Windows text translation from byte-preserving ingestion.

Existing backend API/contract/schema/integration tests all remain in the full
suite, including live browser/HTTP adapter probes. Standalone frontend unit/lint/
build/full browser suites were not rerun: no frontend/shared public contract file
was modified. Historical 42/40 frontend counts are not represented as new results.

## Limitations and D2 handoff

- Revisions remain operator-owned opaque identifiers. D1 seals captured accepted
  bytes but cannot prove they correspond to a Git commit or the existing opaque
  registration snapshot's contents. Delvin must finalize revision custody/freeze
  before agent execution. Keep permitted workspaces stable during indexing.
- Filesystem checks reject static redirects/hardlinks and detect changes during
  capture/indexing, but do not provide an OS-enforced immutable snapshot against
  a hostile concurrent directory writer. This is a local demo trust boundary.
- Python is syntax-aware; other languages and invalid Python use line windows.
  Very long individual source lines fail rather than yielding inaccurate slices.
- General English BGE is small and practical, not a code-specialized model.
  Tokenizer truncation at 512 tokens can reduce coverage of dense chunks. Assess
  quality on actual incidents, token distributions, and code languages before D2.
- Synchronous local embedding/search is an internal service. Future orchestration
  must define worker scheduling, cancellation/time budgets, authorization, audits,
  and concurrency policy. Prefer one indexing writer for this prototype.
- Brute-force search, collection JSON and repeated artifact verification are
  intentionally bounded for small demos. No ANN server, production DLP, automatic
  retention/pruning, public Diagnosis endpoint, or LLM output contract is claimed.

Questions for Delvin: (1) source revision custody and immutable snapshot protocol;
(2) inline traces versus scoped log refs; (3) existing `hypothesis` and
`suggested_direction` fields versus proposed `root_cause`/`suggested_fix` names;
(4) how partial/exact-only evidence maps to manual review; (5) authorization,
cancellation and audit ownership; (6) retention of historical citations.

D1 retrieval is ready for review and D2 contract agreement. D2 has not started.
No commit or push was performed. Any publishing of the uncommitted Phase 3
foundation and D1 work requires a separate reviewed/authorized handoff on
`Diagno-Agent` only; `main` and the remote references were not modified.
