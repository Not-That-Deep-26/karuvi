"""
Unit and integration tests for Karuvi DeepWiki-Pro-Max CLI commands.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


FIXTURE_PATH = str(Path(__file__).parent.parent / "fixtures" / "simple_layered")


def test_cli_explain_repo_command():
    """Verify `karuvi explain <repo>` generates architecture technical guide."""
    result = subprocess.run(
        [sys.executable, "cli.py", "explain", FIXTURE_PATH],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Repository Technical Architecture Guide" in result.stdout
    assert "Executive Summary" in result.stdout
    assert "Architecture" in result.stdout


def test_cli_explain_arch_command():
    """Verify `karuvi explain <repo> arch` generates architecture subsystems view."""
    result = subprocess.run(
        [sys.executable, "cli.py", "explain", FIXTURE_PATH, "arch"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Architectural Subsystems & Flow Guide" in result.stdout
    assert "Core Components & Subsystems" in result.stdout


def test_cli_explain_module_command():
    """Verify `karuvi explain <repo> <module>` generates module inspection."""
    result = subprocess.run(
        [sys.executable, "cli.py", "explain", FIXTURE_PATH, "services/auth.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Module Architecture Explanation: services/auth.py" in result.stdout
    assert "BRIDGE" in result.stdout


def test_cli_why_command():
    """Verify `karuvi <repo> --why <source> <target>` explains dependency intent."""
    result = subprocess.run(
        [sys.executable, "cli.py", FIXTURE_PATH, "--why", "api/main.py", "services/auth.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Dependency Intent: api/main.py ➔ services/auth.py" in result.stdout
    assert "Security Enforcement" in result.stdout
    assert "authenticate" in result.stdout


def test_cli_explore_export(tmp_path: Path):
    """Verify `karuvi explore <repo> --html <path>` exports Living Codebase Atlas."""
    out_html = tmp_path / "test_atlas.html"
    result = subprocess.run(
        [sys.executable, "cli.py", FIXTURE_PATH, "--html", str(out_html), "--architecture"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert out_html.exists()
    content = out_html.read_text(encoding="utf-8")
    assert "Living Codebase Atlas" in content
    assert "window.KARUVI_DATA =" in content
