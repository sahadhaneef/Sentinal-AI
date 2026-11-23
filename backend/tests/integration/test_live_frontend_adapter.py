import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from alembic.config import Config

from alembic import command
from app.core.config import BACKEND_ROOT


@pytest.mark.integration
def test_actual_http_frontend_adapter_accepts_running_fastapi(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    node = shutil.which("node")
    assert node, "Install Node.js and run npm ci in frontend before live contract tests."
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = {
        **os.environ,
        "SENTINEL_ENVIRONMENT": "test",
        "SENTINEL_DATABASE_URL": f"sqlite:///{(tmp_path / 'live.db').as_posix()}",
    }
    monkeypatch.setenv("SENTINEL_DATABASE_URL", environment["SENTINEL_DATABASE_URL"])
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        base = f"http://127.0.0.1:{port}/api/v1"
        with httpx.Client(timeout=1, trust_env=False) as client:
            deadline = time.monotonic() + 15
            while True:
                assert process.poll() is None, "Uvicorn exited during startup"
                try:
                    if client.get(f"{base}/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline, "Uvicorn did not become ready"
                time.sleep(0.1)
        result = subprocess.run(
            [node, str(BACKEND_ROOT / "scripts/check_frontend_contract.mjs"), base],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        assert result.returncode == 0, result.stderr
        assert '"health":"passed"' in result.stdout
        assert '"error_envelope":"passed"' in result.stdout
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
