"""Reuse existing migrated source/context fixtures."""

from tests.diagnosis.reasoning.conftest import scenario as reasoning_scenario
from tests.diagnosis.reasoning.conftest import scenario_factory as reasoning_factory

scenario = reasoning_scenario
scenario_factory = reasoning_factory
