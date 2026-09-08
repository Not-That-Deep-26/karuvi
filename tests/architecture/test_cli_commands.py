"""
Unit and integration tests for Karuvi CLI commands.
"""
from __future__ import annotations

import json
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest


FIXTURE_PATH = str(Path(__file__).parent.parent / "fixtures" / "simple_layered")


def test_cli_onboard_command():
    """Verify `karuvi onboard <repo> --level beginner` runs cleanly."""
    result = subprocess.run(
        [sys.executable, "-m", "karuvi", "onboard", FIXTURE_PATH, "--level", "beginner"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Karuvi Progressive Codebase Onboarding Course" in result.stdout
    assert "Step 1/4" in result.stdout
    assert "UserRepository" in result.stdout










def test_cli_explore_export(tmp_path: Path):
    """Verify `karuvi explore <repo> --html <path>` exports Living Codebase Atlas."""
    out_html = tmp_path / "test_atlas.html"
    result = subprocess.run(
        [sys.executable, "-m", "karuvi", FIXTURE_PATH, "--html", str(out_html), "--architecture"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert out_html.exists()
    content = out_html.read_text(encoding="utf-8")
    assert "Living Codebase Atlas" in content
    assert "window.KARUVI_DATA =" in content


def test_cli_plain_html_export_without_architecture(tmp_path: Path):
    """`--html` without `--architecture` must still build the arch model lazily."""
    out_html = tmp_path / "plain_atlas.html"
    result = subprocess.run(
        [sys.executable, "-m", "karuvi", FIXTURE_PATH, "--html", str(out_html)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out_html.exists()
    content = out_html.read_text(encoding="utf-8")
    assert "window.KARUVI_DATA =" in content


def test_cli_export_subcommand(tmp_path: Path):
    """`karuvi export <repo>` writes the default JSON + HTML outputs into the repo."""
    src = Path(FIXTURE_PATH)
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)

    result = subprocess.run(
        [sys.executable, "-m", "karuvi", "export", str(dst)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    json_out = dst / "karuvi_analysis.json"
    html_out = dst / "karuvi_atlas.html"
    assert json_out.exists()
    assert html_out.exists()
    assert json.loads(json_out.read_text(encoding="utf-8"))["repository"] == str(dst.resolve())
    assert "window.KARUVI_DATA =" in html_out.read_text(encoding="utf-8")


def test_export_outputs_both(tmp_path: Path):
    """export_outputs() writes valid JSON and a payload-bearing HTML in one call."""
    from karuvi.cli import analyze_repository, export_outputs

    repo = Path(FIXTURE_PATH).resolve()
    parsed_modules, _index, builder = analyze_repository(repo)
    json_out = tmp_path / "out.json"
    html_out = tmp_path / "out.html"

    written = export_outputs(
        repo,
        parsed_modules,
        builder,
        json_path=json_out,
        html_path=html_out,
    )
    assert set(written) == {"json", "html"}
    assert json.loads(json_out.read_text(encoding="utf-8"))["repository"] == str(repo)
    assert "window.KARUVI_DATA =" in html_out.read_text(encoding="utf-8")


def test_bare_run_autoserves_atlas(tmp_path: Path):
    """Bare `karuvi <repo>` (no flags) exports the Atlas and auto-serves it."""
    src = Path(FIXTURE_PATH)
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    proc = subprocess.Popen(
        [sys.executable, "-m", "karuvi", str(dst), "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        served = False
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/karuvi_atlas.html", timeout=1) as resp:
                    if resp.status == 200:
                        served = True
                        break
            except Exception:
                pass
            time.sleep(0.3)
        assert served, "atlas was not served on the expected URL"
    finally:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    out = proc.stdout.read() if proc.stdout else ""
    assert "Server stopped." in out
    assert f"Serving Living Codebase Atlas at: http://127.0.0.1:{port}/karuvi_atlas.html" in out
    assert (dst / "karuvi_atlas.html").exists()
    assert "window.KARUVI_DATA =" in (dst / "karuvi_atlas.html").read_text(encoding="utf-8")


def test_cli_explore_runs_classic_dashboard():
    """`karuvi explore <repo>` now runs the former default dashboard (no auto-serve)."""
    result = subprocess.run(
        [sys.executable, "-m", "karuvi", "explore", FIXTURE_PATH],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Karuvi — Whole Repository Analysis" in result.stdout
    assert "Serving Living Codebase Atlas at:" not in result.stdout


def test_atlas_server_serves_html(tmp_path: Path):
    """The atlas HTTP server returns the exported HTML file over localhost."""
    from karuvi.cli import _atlas_server

    html_file = tmp_path / "atlas.html"
    expected = "<html><body>window.KARUVI_DATA = {}</body></html>"
    html_file.write_text(expected, encoding="utf-8")

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    server = _atlas_server(html_file, port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        body = None
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/atlas.html", timeout=1) as resp:
                    assert resp.status == 200
                    body = resp.read().decode("utf-8")
                break
            except Exception:
                time.sleep(0.1)
        assert body == expected
    finally:
        server.shutdown()
        server.server_close()
