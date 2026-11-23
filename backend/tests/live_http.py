"""Own and clean up a real local backend process for integration checks."""

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from app.core.config import BACKEND_ROOT, Settings


def available_port() -> int:
    """Reserve an available loopback port briefly without touching existing services."""
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        return reservation.getsockname()[1]


@contextmanager
def running_backend(settings: Settings) -> Iterator[str]:
    """Start only the supplied isolated database, never migrate or seed implicitly."""
    port = available_port()
    environment = dict(os.environ)
    values = settings.model_dump(mode="json", exclude={"operator_token"})
    for name, value in values.items():
        environment[f"SENTINEL_{name.upper()}"] = (
            json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        )
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
                assert process.poll() is None, "Local backend exited during startup"
                try:
                    if client.get(base + "/health").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                assert time.monotonic() < deadline, "Local backend did not become ready"
                time.sleep(0.1)
        yield base
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
