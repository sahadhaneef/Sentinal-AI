# Agent workflow boundary

No agents execute in Phase 1. Health is backend liveness, not an agent-health claim. The frontend's public animation and learning demo remain explanatory/simulated.

The future Manager (Delvin) coordinates Monitoring (Neha), Diagnosis and Code RAG (Sahad), Repair (Yadhulakshmi), Testing (Sravan), and Reporting (Neha). Human approval is a separate gate, never a seventh agent.

Required typed handoffs and exact wire states are frozen in `FRONTEND_BACKEND_CONTRACT.md`. Later persistence must commit each transition with audit evidence, bound retries, idempotency and concurrency protection. Validate before approval; approval never applies a patch; apply is a separate authorized operation; verification precedes resolved; failed restoration remains unresolved/manual action. No fallback should invent evidence when a stage is unavailable.

The seven frontend fixtures are test scenarios, not backend seed records. Phase 1 cannot seed, diagnose, test, approve, apply or restore the demo. Instructions for those operations must be added only with their tested implementations.
