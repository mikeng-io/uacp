"""Tests for skills/uacp-council/scripts/check_model_authorized.py — the fail-closed
model-authorization gate (uacp-bridge). These assert the *security property*: an
unapproved model is rejected (exit 3), an approved one passes (exit 0)."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "uacp-council" / "scripts" / "check_model_authorized.py"
REAL_CONFIG = Path(__file__).resolve().parents[3] / "config" / "uacp.toml"


def _run(bridge: str, model: str, cfg: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), bridge, model, f"--config={cfg}"],
        capture_output=True, text=True,
    )


def test_opencode_minimax_is_rejected_against_real_config():
    # The rejected swap must NOT be authorized.
    res = _run("opencode", "minimax-m3", REAL_CONFIG)
    assert res.returncode == 3, res.stdout + res.stderr
    assert json.loads(res.stdout)["authorized"] is False


def test_opencode_approved_model_passes_against_real_config():
    res = _run("opencode", "mimo-v2.5", REAL_CONFIG)
    assert res.returncode == 0, res.stdout + res.stderr
    assert json.loads(res.stdout)["authorized"] is True


def test_hermes_empty_allowlist_is_fail_closed():
    res = _run("hermes", "anything/at-all", REAL_CONFIG)
    assert res.returncode == 3, "empty allowlist under enforcement must reject"


def test_single_provider_known_model_authorized():
    # codex maps to provider openai; gpt-5-4 is an alias there.
    res = _run("codex", "gpt-5-4", REAL_CONFIG)
    assert res.returncode == 0, res.stdout + res.stderr


def test_single_provider_unknown_model_rejected():
    res = _run("codex", "gpt-9-ultra-leaked", REAL_CONFIG)
    assert res.returncode == 3, "an unknown model for the provider must be rejected"


def test_gate_disabled_authorizes_everything(tmp_path: Path):
    cfg = tmp_path / "uacp.toml"
    cfg.write_text(textwrap.dedent("""
        [bridges.defaults]
        enforce_model_allowlist = false
        [bridges.opencode]
        allowed_models = []
    """))
    res = _run("opencode", "minimax-m3", cfg)
    assert res.returncode == 0, "with the gate disabled, authorization is a no-op"
    assert "disabled" in json.loads(res.stdout)["reason"]


def test_usage_error_on_missing_args():
    res = subprocess.run([sys.executable, str(SCRIPT), "opencode"], capture_output=True, text=True)
    assert res.returncode == 2
