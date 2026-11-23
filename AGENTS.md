# Diagnosis Agent and Code RAG branch workflow

These restrictions apply to SENTINEL AI Diagnosis Agent and Code RAG development.
Repository: https://github.com/sahadhaneef/Sentinal-AI

## Branch and work preservation

- Work only on the existing `Diagno-Agent` branch, tracking
  `origin/Diagno-Agent`. Never create another development branch for this workflow.
- Before development, inspect the current branch, remotes, working-tree status
  and the relationship to `origin/Diagno-Agent`. Preserve existing work before
  any branch switch; never assume the remote contains the completed Phase 3 code.
- If uncommitted changes prevent a safe switch, stop and explain the options.
  Never use hard reset, forced checkout, git clean, or other destructive shortcuts.
- Keep unrelated changes separate. The initial Phase 3 foundation is uncommitted
  local work and is not present on the remote branch. Do not silently bundle it
  into Diagnosis commits. Review and separately authorize any foundation handoff
  needed before publishing work that depends on it.
- Local preservation archives/manifests are under ignored `.tools/branch-safety/`.
  They are local backups, not proof that anything has been published to GitHub.

## Commit and push gates

- Immediately before every commit or push, verify that
  `git branch --show-current` returns exactly `Diagno-Agent`; stop otherwise.
- Before a commit, inspect `git diff --cached --name-status` and the staged diff.
  Stage explicit intended paths; never blindly stage the whole dirty workspace.
- Exclude credentials, real environment files, local databases, virtual
  environments, tooling, backups, build outputs and generated test artifacts.
  Credential-free `.env.example` templates may be reviewed as source.
- The only permitted push destination is `git push origin Diagno-Agent`.
  Never push Diagnosis/Code RAG changes to `main`, and never force-push.
- Do not merge into `main` or create a pull request without explicit permission.

## Development and reporting

- Implement only the assigned Diagnosis Agent and Code RAG responsibilities.
  Preserve the frontend, Phase 3 APIs and other agents' ownership boundaries.
- Follow `backend/AGENTS.md` unchanged: PEP 8, Python 3.12, typed code, PEP 257,
  existing Ruff configuration and its 100-character limit, and required checks.
- After each phase report the branch, changed files, commit SHA if any, push
  outcome, remote branch updated (if any), actual test results, and confirmation
  that the local and remote `main` references were not modified.
