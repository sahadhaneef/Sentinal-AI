"""A real loopback timeout must not be reported as successful model reasoning."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.agents.diagnosis.quality.service import QualityDiagnosisService
from app.agents.diagnosis.reasoning.config import DiagnosisSettings
from tests.diagnosis.reasoning.conftest import Scenario


@pytest.mark.integration
def test_provider_socket_timeout_is_manual_review(scenario: Scenario) -> None:
    class SlowHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers["Content-Length"]))
            threading.Event().wait(0.4)
            self.close_connection = True

    with ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = DiagnosisSettings(
                provider="ollama",
                model="timeout-test-only",
                base_url=f"http://127.0.0.1:{server.server_port}",
                timeout_seconds=0.1,
            )
            checked = QualityDiagnosisService(
                scenario.harness.engine,
                scenario.harness.settings,
                scenario.harness.service,
                config=config,
            ).diagnose(scenario.request)
            assert checked.result.status == "manual_review"
            assert checked.result.error.code == "LLM_UNAVAILABLE"
            assert checked.result.hypotheses == []
        finally:
            server.shutdown()
            thread.join(timeout=2)
