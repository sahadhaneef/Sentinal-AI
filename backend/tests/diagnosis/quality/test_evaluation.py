"""Labeled cases assert deterministic safety observations, not live-model accuracy."""

import json
from pathlib import Path

from app.agents.diagnosis.quality.evaluate import evaluate
from app.agents.diagnosis.reasoning.contracts import ReasoningContext
from tests.diagnosis.conftest import TestEncoder


class LabeledFixtureProvider:
    """Generate from error context only; evaluation labels never enter this provider."""

    name = "deterministic-quality-test-only"

    def reason(self, context: ReasoningContext) -> str:
        hypothesis = (
            "The denominator may be zero."
            if context.error_type == "ZeroDivisionError"
            else "The name key may be absent from the profile."
        )
        return json.dumps(
            {
                "hypotheses": [
                    {
                        "statement": hypothesis,
                        "evidence_ids": [context.evidence[0].evidence_id],
                        "uncertainty": "Runtime input values have not been observed.",
                    }
                ],
                "confidence_label": "medium",
                "uncertainty": "No execution was performed.",
                "suggested_direction": "Review the validated source and incident input values.",
                "needs_manual_review": False,
            }
        )


def test_labeled_dataset_observations_and_source_preservation(tmp_path: Path) -> None:
    report = evaluate(tmp_path, TestEncoder(), LabeledFixtureProvider())
    assert len(report["cases"]) == 9
    assert report["provider_calls"] == 2
    for case in report["cases"]:
        assert case["status_matches_label"], case
        assert case["source_unchanged"]
        if case["expected_file_retrieved"] is not None:
            assert case["expected_file_retrieved"], case
        if case["hypothesis_terms_present"] is not None:
            assert case["hypothesis_terms_present"], case
    by_name = {case["case_id"]: case for case in report["cases"]}
    assert "CONFLICTING_ERROR_TYPES" in by_name["contradictory_exception"]["quality_codes"]
    assert "REPORTED_KEY_NOT_SUPPORTED" in by_name["key_not_supported"]["quality_codes"]
