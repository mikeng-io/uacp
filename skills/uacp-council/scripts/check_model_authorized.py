#!/usr/bin/env python3
"""Model authorization gate — uacp-bridge fail-closed model allowlist (real teeth).

Bridges are reference docs an LLM follows; "fail-closed" is only as strong as a
check the orchestrator actually runs. This is that check: given a bridge and the
model it intends to use, exit 0 iff the model is AUTHORIZED, else non-zero so the
orchestrator SKIPs. See uacp-bridge/SKILL.md "Model authorization (fail-closed)".

Usage:
    check_model_authorized.py <bridge> <model> [--config PATH]

Exit codes: 0 authorized · 3 NOT authorized (SKIP) · 2 usage/config error.
Prints a JSON verdict to stdout: {bridge, model, authorized, reason}.

Authorization rules:
  - enforce_model_allowlist=false  -> authorized (gate disabled).
  - Multi-provider bridges (opencode, hermes): model MUST be in
    [bridges.<bridge>].allowed_models; empty list -> NOT authorized.
  - Single-provider bridges (claude/codex/gemini/kimi/reasonix): model must match
    a concrete_id or alias under that bridge's provider in [models.providers.*].
"""
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

# Single-provider bridge -> provider key in [models.providers.*].
_BRIDGE_PROVIDER = {
    "claude": "anthropic",
    "codex": "openai",
    "gemini": "google",
    "kimi": "moonshot",
    "reasonix": "deepseek",
}
_MULTI_PROVIDER = {"opencode", "hermes"}


def _find_config(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config" / "uacp.toml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("config/uacp.toml not found from script location")


def authorize(bridge: str, model: str, cfg: dict) -> tuple[bool, str]:
    bridges = cfg.get("bridges", {})
    enforce = bridges.get("defaults", {}).get("enforce_model_allowlist", False)
    if not enforce:
        return True, "enforce_model_allowlist=false (gate disabled)"

    if bridge in _MULTI_PROVIDER:
        allowed = bridges.get(bridge, {}).get("allowed_models", [])
        if model in allowed:
            return True, f"in {bridge}.allowed_models"
        return False, (
            f"{model!r} not in {bridge}.allowed_models={allowed!r} "
            f"(multi-provider bridge requires explicit allowlist)"
        )

    provider = _BRIDGE_PROVIDER.get(bridge)
    if provider is None:
        return False, f"unknown bridge {bridge!r}"
    models = cfg.get("models", {}).get("providers", {}).get(provider, {}).get("models", {})
    # authorized if model matches an alias key OR its concrete_id
    aliases = set(models.keys())
    concrete = {m.get("concrete_id") for m in models.values() if isinstance(m, dict)}
    if model in aliases or model in concrete:
        return True, f"resolved from [models.providers.{provider}]"
    return False, (
        f"{model!r} is not a known alias/concrete_id for provider {provider!r} "
        f"(aliases={sorted(aliases)}, concrete={sorted(c for c in concrete if c)})"
    )


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    cfg_flag = next((a.split("=", 1)[1] for a in argv if a.startswith("--config=")), None)
    if len(args) != 2:
        print("usage: check_model_authorized.py <bridge> <model> [--config=PATH]", file=sys.stderr)
        return 2
    bridge, model = args
    try:
        with open(_find_config(cfg_flag), "rb") as fh:
            cfg = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    ok, reason = authorize(bridge, model, cfg)
    print(json.dumps({"bridge": bridge, "model": model, "authorized": ok, "reason": reason}))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
