import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest


def _find_free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, port = sock.getsockname()
    sock.close()
    return int(port)


def _wait_for_server(url: str, timeout: float = 12.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=0.5):
                return
        except URLError as error:
            last_error = error
        time.sleep(0.1)

    raise RuntimeError(f"Server did not become ready at {url}") from last_error


@pytest.fixture(scope="session")
def app_presets_path() -> str:
    with tempfile.TemporaryDirectory() as tmp_dir:
        presets_path = Path(tmp_dir) / "presets.json"
        presets_path.write_text((Path(__file__).resolve().parents[1] / "presets.json").read_text(encoding="utf-8"), encoding="utf-8")
        yield str(presets_path)


@pytest.fixture(scope="session")
def app_url(app_presets_path: str) -> str:
    port = _find_free_port()
    os.environ["OFFLINEGRAM_TEST_PRESETS_PATH"] = app_presets_path
    env = dict(os.environ)
    env["OFFLINEGRAM_PRESETS_PATH"] = app_presets_path
    env["OFFLINEGRAM_TEST_PRESETS_PATH"] = app_presets_path
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_server(url)
        yield url
    finally:
        os.environ.pop("OFFLINEGRAM_TEST_PRESETS_PATH", None)
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
