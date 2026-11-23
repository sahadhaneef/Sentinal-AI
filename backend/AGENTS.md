# Mandatory backend Python standards

Apply these requirements automatically throughout every remaining SENTINEL AI
backend phase, including generated code, migrations, tests and refactors.

- Follow PEP 8, Python 3.12 conventions and PEP 257 docstrings.
- Indent with four spaces; never use tabs for indentation.
- Use `snake_case` for variables, functions, methods and modules; `PascalCase`
  for classes; `UPPER_SNAKE_CASE` for constants.
- Use descriptive names, appropriate blank lines and Ruff-sorted imports.
- Add type annotations to function parameters and return values. Document public
  modules, classes and functions where appropriate.
- Keep functions readable, avoid unnecessary nesting and duplicated logic, and
  apply SOLID principles where practical.
- Separate routes, services, repositories, schemas and AI agents.
- Handle exceptions appropriately, use structured logging instead of unnecessary
  prints, and never hardcode credentials.
- Add meaningful tests for new functionality and preserve existing tests.
- Review every modified Python file for compliance. Do not rewrite unrelated
  working code solely for formatting.

## Ruff configuration and acceptance

Use the existing `backend/pyproject.toml` lint and formatting configuration.
Its current maximum line length is **100 characters**; preserve that explicit
project setting. Use 88 only if the project no longer specifies a line length.
Do not suppress warnings without a documented reason.

Before completing any backend phase, run these commands from `backend/` using
the project's Python environment:

```sh
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

Fix linting and formatting errors before completion. PEP 8 compliance and passing
Ruff lint, Ruff formatting and relevant automated tests are mandatory acceptance
criteria. Never mark a phase complete with failed required checks. Report actual
commands, results and unresolved issues; never claim an unrun check passed.
