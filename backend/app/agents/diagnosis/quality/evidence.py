"""Conservative sufficiency checks reusing D1's authoritative citation resolver."""

import ast
import re
import textwrap
from pathlib import PurePosixPath

from app.agents.diagnosis.code_rag.contracts import (
    RetrievalRequest,
    RetrievalResult,
    RetrievedEvidence,
)
from app.agents.diagnosis.code_rag.evidence_store import EvidenceStore
from app.agents.diagnosis.code_rag.stacktrace import hints, matching_path
from app.agents.diagnosis.reasoning.contracts import DiagnosisResult
from app.db.types import validate_relative_key

from .contracts import QualityAssessment, QualityIssue

ERROR_LINE = re.compile(r"(?m)^([A-Za-z_]\w*(?:Error|Exception)):\s*(.*)$")
NARRATIVE_PATH = re.compile(
    r"(?P<path>(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+"
    r"\.(?:py|js|jsx|ts|tsx|go|rs|java|c|cpp|h|hpp|yaml|yml|json|toml|"
    r"ini|xml|html|css|sql|sh|ps1|rb|php|kt|swift|txt|md))(?![A-Za-z0-9_])"
    r"(?:(?::|[, ]+line\s+)(?P<line>\d+))?"
)


class EvidencePolicy:
    """Python is the evaluated language; unfamiliar evidence requires human review."""

    def __init__(self, minimum_semantic_score: float = 0.6) -> None:
        if not 0 <= minimum_semantic_score <= 1:
            raise ValueError("Semantic threshold must be between zero and one")
        self.minimum_semantic_score = minimum_semantic_score

    def assess(
        self, request: RetrievalRequest, retrieval: RetrievalResult, resolver: EvidenceStore
    ) -> QualityAssessment:
        issues: list[QualityIssue] = []
        verified: list[str] = []
        snapshots: set[str] = set()
        for item in retrieval.evidence:
            try:
                RetrievedEvidence.model_validate(item.model_dump())
                validate_relative_key(item.file_path)
                if item.start_line < 1 or item.end_line < item.start_line:
                    raise ValueError("Invalid citation range")
                resolved = resolver.resolve(
                    request.application_id,
                    request.repository_revision,
                    item.source_snapshot_ref,
                    item.evidence_id,
                )
                if any(
                    resolved[key] != value
                    for key, value in item.model_dump().items()
                    if key in resolved
                ):
                    raise ValueError("Citation metadata mismatch")
            except Exception:
                issues.append(
                    QualityIssue(
                        code="UNVERIFIABLE_CITATION",
                        action="Re-index this revision and restore its source artifacts.",
                    )
                )
                continue
            verified.append(item.evidence_id)
            snapshots.add(item.source_snapshot_ref)
            if item.language != "python" or PurePosixPath(item.file_path).suffix != ".py":
                issues.append(
                    QualityIssue(
                        code="LANGUAGE_NOT_EVALUATED",
                        action="Ask a reviewer to inspect this language before accepting a cause.",
                    )
                )
        if len(snapshots) > 1:
            issues.append(
                QualityIssue(
                    code="CONFLICTING_SNAPSHOTS",
                    action="Retrieve one immutable snapshot at the requested revision.",
                )
            )
        if not retrieval.evidence:
            issues.append(
                QualityIssue(
                    code="INSUFFICIENT_EVIDENCE",
                    action="Index the permitted revision and provide the relevant stack trace.",
                )
            )
        frames = hints(request.stack_trace)
        paths = {item.file_path for item in retrieval.evidence}
        exact = [
            item
            for item in retrieval.evidence
            if any(
                matching_path(frame.file_path, paths) == item.file_path
                and item.start_line <= frame.line <= item.end_line
                for frame in frames
            )
        ]
        if any(item.exact_tier == 2 and item not in exact for item in retrieval.evidence):
            issues.append(
                QualityIssue(
                    code="STACK_METADATA_CONFLICT",
                    action="Rebuild metadata from the stack and exact source ranges.",
                )
            )
        if frames and not exact:
            issues.append(
                QualityIssue(
                    code="UNRESOLVED_STACK",
                    action="Confirm the stack file and line belong to the indexed revision.",
                )
            )
        elif (
            retrieval.evidence
            and not exact
            and not any(
                item.semantic_score is not None
                and item.semantic_score >= self.minimum_semantic_score
                for item in retrieval.evidence
            )
        ):
            issues.append(
                QualityIssue(
                    code="WEAK_SEMANTIC_EVIDENCE",
                    action="Provide a stack frame or stronger revision-bound evidence.",
                )
            )
        errors = ERROR_LINE.findall(request.stack_trace)
        if errors and errors[-1][0] != request.error_type.rsplit(".", 1)[-1]:
            issues.append(
                QualityIssue(
                    code="CONFLICTING_ERROR_TYPES",
                    action="Reconcile the incident error type with the terminal exception.",
                )
            )
        key_match = re.fullmatch(r"['\"]([^'\"]+)['\"]", errors[-1][1].strip()) if errors else None
        if request.error_type == "KeyError" and key_match and exact:
            self._key_support(exact, key_match[1], issues)
        return QualityAssessment(issues=issues, verified_evidence_ids=verified)

    def _key_support(
        self, evidence: list[RetrievedEvidence], key: str, issues: list[QualityIssue]
    ) -> None:
        parsed = []
        for item in evidence:
            if item.language != "python":
                continue
            try:
                parsed.append(ast.parse(textwrap.dedent(item.excerpt)))
            except (SyntaxError, ValueError, RecursionError):
                issues.append(
                    QualityIssue(
                        code="SOURCE_CONTEXT_INCOMPLETE",
                        action="Provide a complete Python source span for the reported KeyError.",
                    )
                )
        if parsed and not any(
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == key
            for tree in parsed
            for node in ast.walk(tree)
        ):
            issues.append(
                QualityIssue(
                    code="REPORTED_KEY_NOT_SUPPORTED",
                    action=(
                        "The span does not show this direct key access; "
                        "inspect alternate causes or obtain more context."
                    ),
                )
            )

    def check_findings(self, result: DiagnosisResult) -> list[QualityIssue]:
        """Reject narrative references outside the verified citation ranges and execution claims."""
        issues = []
        text = "\n".join(
            [
                result.suggested_direction,
                result.uncertainty,
                *(
                    value
                    for item in result.hypotheses
                    for value in (item.statement, item.uncertainty)
                ),
            ]
        )
        for match in NARRATIVE_PATH.finditer(text.replace("\\", "/")):
            path = match["path"]
            line = int(match["line"]) if match["line"] and len(match["line"]) < 10 else None
            if (match["line"] and line is None) or not any(
                item.file_path == path
                and (line is None or item.start_line <= line <= item.end_line)
                for item in result.evidence
            ):
                issues.append(
                    QualityIssue(
                        code="NARRATIVE_CITATION_INVALID",
                        action="Remove unsupported file/line claims; use returned evidence.",
                    )
                )
        if re.search(r"\b(definitely|proven root cause|confirmed root cause)\b|100%", text, re.I):
            issues.append(
                QualityIssue(
                    code="UNSUPPORTED_CERTAINTY",
                    action="Restate the cause as a hypothesis with explicit uncertainty.",
                )
            )
        if re.search(
            r"\b(I (?:ran|executed|applied)|tests? (?:all )?passed|"
            r"recovery (?:was )?verified|patch (?:was )?applied)\b",
            text,
            re.I,
        ):
            issues.append(
                QualityIssue(
                    code="UNSUPPORTED_EXECUTION_CLAIM",
                    action="Remove execution/recovery claims; Diagnosis has no execution tools.",
                )
            )
        return issues
