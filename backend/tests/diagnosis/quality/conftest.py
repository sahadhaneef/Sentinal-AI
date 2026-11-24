"""Reuse the D2 scenario fixtures without copying their database setup."""

from tests.diagnosis.reasoning.conftest import scenario as reasoning_scenario
from tests.diagnosis.reasoning.conftest import scenario_factory as reasoning_factory

scenario = reasoning_scenario
scenario_factory = reasoning_factory
