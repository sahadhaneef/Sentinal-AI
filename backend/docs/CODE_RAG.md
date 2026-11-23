# Code RAG boundary — Sahad

Code retrieval and LLM diagnosis are not implemented in Phase 1. No embeddings, provider client, generated repair or API secret is configured. Health cannot be used to infer retrieval readiness.

The later Diagnosis module must index only the explicitly permitted demo revision, exclude secrets/generated/dependency/binary files, and preserve relative path, symbol, line range, exact revision and content hash. Start with deterministic lexical retrieval and prove citations resolve before adding optional embedding providers. Logs and retrieved code are data, not instructions.

Use validated structured diagnosis output matching the existing frontend schema: completed or manual_review, hypothesis, confidence label, uncertainty, repair direction and evidence references/excerpts. Missing evidence must lead to manual review; do not fabricate citations. Provider secrets stay server-side and outside Git. Provider configuration and benchmark/setup instructions belong to Phase 6, not a fake foundation implementation.
