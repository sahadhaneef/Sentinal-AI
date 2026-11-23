"""Real TypeScript adapter and browser checks against isolated persisted records."""

import os
import shutil
import subprocess

import pytest

from app.core.config import BACKEND_ROOT, Settings
from tests.live_http import available_port, running_backend


@pytest.mark.integration
def test_actual_adapter_reads_persisted_domain_graph(
    api_settings: Settings, populated: None
) -> None:
    node = shutil.which("node")
    assert node, "Node.js and frontend dependencies are required."
    with running_backend(api_settings) as base:
        result = subprocess.run(
            [node, str(BACKEND_ROOT / "scripts/check_frontend_contract.mjs"), base, "persisted"],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        assert result.returncode == 0, result.stderr
        assert '"persisted_reads":"passed"' in result.stdout


def check_browser(base: str, ui_port: int, mode: str) -> None:
    """Exercise UI reads without intercepting responses or changing the selected adapter."""
    node = shutil.which("node")
    assert node, "Node.js and installed Playwright Chromium are required."
    result = subprocess.run(
        [node, str(BACKEND_ROOT / "scripts/check_frontend_browser.mjs"), base, str(ui_port), mode],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
        env=dict(os.environ)
        | {"PLAYWRIGHT_BROWSERS_PATH": str(BACKEND_ROOT.parent / "frontend/.playwright")},
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"live_browser":"passed"' in result.stdout


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["persisted", "empty", "unavailable"])
def test_real_frontend_browser_uses_database_http(
    api_settings: Settings,
    request: pytest.FixtureRequest,
    mode: str,
) -> None:
    if mode == "persisted":
        request.getfixturevalue("populated")
    ui_port = available_port()
    if mode == "unavailable":
        check_browser(f"http://127.0.0.1:{available_port()}/api/v1", ui_port, mode)
        return
    settings = api_settings.model_copy(update={"cors_origins": [f"http://127.0.0.1:{ui_port}"]})
    with running_backend(settings) as base:
        check_browser(base, ui_port, mode)
