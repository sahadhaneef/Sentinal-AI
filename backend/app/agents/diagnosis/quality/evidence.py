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

    def check_operand(
        self, request: RetrievalRequest, result: DiagnosisResult
    ) -> list[QualityIssue]:
        """Check the immediate cause for unambiguous Python zero division."""
        if request.error_type != "ZeroDivisionError" or not result.hypotheses:
            return []
        frames = hints(request.stack_trace)
        if not frames:
            return [self._operand_issue()]
        frame = frames[-1]
        path = matching_path(frame.file_path, {item.file_path for item in result.evidence})
        for hypothesis in result.hypotheses:
            candidates = set()
            for item in result.evidence:
                if item.evidence_id not in hypothesis.evidence_ids or item.file_path != path:
                    continue
                if not item.start_line <= frame.line <= item.end_line:
                    continue
                candidates.update(self._divisor_names(item, frame.line))
            if len(candidates) != 1:
                return [self._operand_issue()]
            divisor = re.escape(next(iter(candidates)))
            # Require a relation, not merely independent occurrences of the identifier and zero.
            if not re.search(
                rf"\b{divisor}\b.?(?:\s+(?:may|might|could|must)(?:\s+have)?"
                rf")?\s+(?:be|been|was|is|being|equals?)\s+(?:zero|0)\b"
                rf"|\bzero\s+(?:value\s+of\s+|for\s+)?{divisor}\b",
                hypothesis.statement,
                re.I,
            ):
                return [self._operand_issue()]
        return []

    @staticmethod
    def _operand_issue() -> QualityIssue:
        return QualityIssue(
            code="UNVERIFIED_CAUSAL_OPERAND",
            action="Identify the zero divisor in an unambiguous cited failing operation.",
        )

    @staticmethod
    def _divisor_names(item: RetrievedEvidence, line: int) -> set[str]:
        if item.language != "python":
            return set()
        try:
            tree = ast.parse(textwrap.dedent(item.excerpt))
        except (SyntaxError, ValueError, RecursionError):
            return set()
        offset = line - item.start_line + 1
        operations = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.BinOp)
            and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod))
            and node.lineno <= offset <= node.end_lineno
        ]
        if len(operations) == 1 and isinstance(operations[0].right, ast.Name):
            return {operations[0].right.id}
        return set()

    def check_findings(self, result: DiagnosisResult) -> list[QualityIssue]:
        """Reject narrative references outside the verified citation ranges and execution claims."""
        issues = []
        for hypothesis in result.hypotheses:
            claim = hypothesis.statement
            excerpts = [
                item.excerpt
                for item in result.evidence
                if item.evidence_id in hypothesis.evidence_ids
            ]
            prompt_echo = re.search(r"\b(user message|data envelope|system prompt)\b", claim, re.I)
            zero_numerator = re.search(
                r"\b(?:zero numerator|numerator (?:is|was|being|equals) zero)\b", claim, re.I
            )
            simple_division = any(
                re.search(r"\b(?:return|yield)\s+\w+\s*(?://|/)\s*\w+\s*$", line)
                for excerpt in excerpts
                for line in excerpt.splitlines()
            )
            if (prompt_echo and not any(prompt_echo[0].lower() in x.lower() for x in excerpts)) or (
                zero_numerator and simple_division and re.search(r"\bdivi\w+\b", claim, re.I)
            ):
                issues.append(
                    QualityIssue(
                        code="UNSUPPORTED_CAUSAL_CLAIM",
                        action="Ground the proposed cause in the cited application operation.",
                    )
                )
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
