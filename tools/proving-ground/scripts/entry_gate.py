#!/usr/bin/env python3
"""S1 ENTRY GATE (design/proving-ground/50-plan.md, verbatim requirements).

Proves the containerized boundary that S0 deliberately left unverified. Four requirements, each
PASS/FAIL with cited evidence:

  R1  BUILD          -- the hermes-bare cell image builds.
  R2  ADAPTER        -- the ACP adapter is present in-image (`hermes acp --check`).
  R3  ROUNDTRIP      -- a full ACP round-trip from the runner INTO the container yields a real model
                        reply via the injected endpoint (positive control -> host ollama).
  R4  ENV_USED       -- the injected env contract is received AND USED: a NEGATIVE control with an
                        unreachable endpoint must FAIL. A reply despite a dead endpoint would mean
                        the env was ignored, so R4 passes only when positive succeeds and negative
                        does not.

If any requirement FAILs the gate STOPS with a non-zero exit and a clear record -- a failed gate
with evidence is a good outcome (the boundary defect is the finding); smoke must NOT run past it.

Emits: tools/proving-ground/records/S1-entry-gate.md

Usage:  python3 scripts/entry_gate.py [--image TAG] [--model qwen3.5:4b] [--skip-build]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

from acp_client import run_prompt  # noqa: E402
from cells import (  # noqa: E402
    ENV_API_KEY,
    ENV_BASE_URL,
    ENV_MODEL_ID,
    HERMES_BARE_IMAGE,
    HOST_OLLAMA_OPENAI_URL,
    SMOKE_MODEL_ID,
)

IMAGE_DIR = PKG / "images" / "hermes"
RECORD = PKG / "records" / "S1-entry-gate.md"
# The ACP transcripts ARE the runner-side ground truth (10-topology); a gate record whose raw
# exchange evaporated with a TemporaryDirectory would be unauditable. Persisted + committed.
TRANSCRIPT_DIR = PKG / "records" / "entry-gate"
DEAD_ENDPOINT = "http://host.docker.internal:1/v1"  # port 1: connection refused
PONG_PROMPT = "Reply with exactly the single word: PONG"
# Deliberately YAML-hostile (quote, backslash, sed metacharacters — newline-free so it stays a
# valid HTTP header): ollama ignores auth, so R3 only passes if the entrypoint renders this
# opaque value into config.yaml as data, proving the env contract survives hostile credentials.
GATE_API_KEY = 'pg-s1"quote\\back|pipe&amp'


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _run(cmd: list[str], timeout: float) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except OSError as exc:
        # Docker absent/unexecutable must produce a FAILED requirement with a written record —
        # the gate's contract is fail-with-evidence, never a traceback with no record.
        return 127, "", f"spawn failed: {exc}"
    except subprocess.TimeoutExpired as exc:
        # TimeoutExpired carries bytes even under text=True in typeshed; decode defensively.
        out = (
            exc.stdout.decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        err = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        return 124, out, err + f"\n[timed out after {timeout}s]"
    return proc.returncode, proc.stdout, proc.stderr


def _docker_cmd(image: str, base_url: str, model: str, workspace: str) -> list[str]:
    return [
        "docker",
        "run",
        "-i",
        "--rm",
        "--add-host=host.docker.internal:host-gateway",
        "-v",
        f"{workspace}:/workspace",
        "-w",
        "/workspace",
        "-e",
        f"{ENV_BASE_URL}={base_url}",
        "-e",
        f"{ENV_API_KEY}={GATE_API_KEY}",
        "-e",
        f"{ENV_MODEL_ID}={model}",
        image,
    ]


class Req:
    def __init__(self, key: str, title: str) -> None:
        self.key = key
        self.title = title
        self.passed = False
        self.lines: list[str] = []

    def log(self, text: str) -> None:
        self.lines.append(text)

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


def gate(image: str, model: str, skip_build: bool) -> tuple[bool, list[Req], dict]:
    reqs: list[Req] = []
    facts: dict = {"image": image, "model": model, "started_at": _utcnow()}

    # R1 -- build ------------------------------------------------------------------------------
    r1 = Req("R1_BUILD", "Cell image builds")
    reqs.append(r1)
    if skip_build:
        r1.log("--skip-build set; assuming a pre-built image (build not re-verified this run).")
        code, out, err = _run(["docker", "image", "inspect", image], 60)
        r1.passed = code == 0
        r1.log(f"$ docker image inspect {image}  -> exit {code}")
        if code != 0:
            r1.log("image not present; cannot skip build")
    else:
        cmd = ["docker", "build", "-t", image, str(IMAGE_DIR)]
        r1.log(f"$ {' '.join(cmd)}")
        t0 = time.monotonic()
        code, out, err = _run(cmd, timeout=1800)
        dt = time.monotonic() - t0
        r1.passed = code == 0
        r1.log(f"exit {code} in {dt:.0f}s")
        tail = (out + err).strip().splitlines()[-12:]
        r1.log("build tail:\n    " + "\n    ".join(tail))
    facts["build_ok"] = r1.passed
    if not r1.passed:
        return False, reqs, facts  # nothing downstream is meaningful without an image

    # R2 -- adapter present --------------------------------------------------------------------
    r2 = Req("R2_ADAPTER", "ACP adapter present in-image")
    reqs.append(r2)
    cmd = ["docker", "run", "--rm", image, "hermes", "acp", "--check"]
    r2.log(f"$ {' '.join(cmd)}")
    code, out, err = _run(cmd, timeout=120)
    combined = (out + err).strip()
    r2.passed = code == 0 and "OK" in combined.upper()
    r2.log(f"exit {code}; output: {combined[:200]!r}")

    # R3 -- positive round-trip into the container ---------------------------------------------
    r3 = Req("R3_ROUNDTRIP", "Full ACP round-trip into container yields a model reply")
    reqs.append(r3)
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pg-entry-pos-") as ws:
        transcript = TRANSCRIPT_DIR / "pos-transcript.log"
        cmd = _docker_cmd(image, HOST_OLLAMA_OPENAI_URL, model, ws)
        r3.log(f"$ {' '.join(cmd)}")
        r3.log(f"prompt: {PONG_PROMPT!r}  endpoint: {HOST_OLLAMA_OPENAI_URL}")
        pos = run_prompt(
            cmd,
            PONG_PROMPT,
            cwd=ws,
            session_cwd="/workspace",
            timeout=240,
            transcript_path=transcript,
        )
    pos_real = _is_real_reply(pos)
    r3.passed = pos_real
    r3.log(
        f"outcome={pos.outcome} stop_reason={pos.stop_reason} updates={pos.update_count} "
        f"text={pos.text.strip()[:160]!r}"
    )
    if pos.error:
        r3.log(f"acp error: {pos.error}")
    if pos.stderr_tail:
        r3.log("container stderr tail: " + " | ".join(pos.stderr_tail[-4:]))
    facts["positive"] = _reply_facts(pos)

    # R4 -- negative control: env must be USED --------------------------------------------------
    r4 = Req("R4_ENV_USED", "Injected env contract received AND used (dead endpoint must fail)")
    reqs.append(r4)
    with tempfile.TemporaryDirectory(prefix="pg-entry-neg-") as ws:
        transcript = TRANSCRIPT_DIR / "neg-transcript.log"
        cmd = _docker_cmd(image, DEAD_ENDPOINT, model, ws)
        r4.log(f"$ {' '.join(cmd)}")
        r4.log(f"prompt: {PONG_PROMPT!r}  endpoint: {DEAD_ENDPOINT} (unreachable)")
        neg = run_prompt(
            cmd,
            PONG_PROMPT,
            cwd=ws,
            session_cwd="/workspace",
            timeout=180,
            transcript_path=transcript,
        )
    neg_real = _is_real_reply(neg)
    neg_backend_failed = _backend_failed(neg)
    # USED-proof: positive gets a genuine reply AND the negative gets NO genuine reply BECAUSE it
    # reached the injected (dead) endpoint and failed to connect. If the env were ignored, the
    # negative would have reached a working default and returned a real reply; the connection
    # failure against the dead endpoint is therefore positive evidence the injected env drove it.
    r4.passed = pos_real and not neg_real and neg_backend_failed
    r4.log(
        f"negative outcome={neg.outcome} stop_reason={neg.stop_reason} updates={neg.update_count} "
        f"genuine_reply={neg_real} backend_failed={neg_backend_failed} "
        f"text={neg.text.strip()[:160]!r}"
    )
    if neg.error:
        r4.log(f"acp error: {neg.error}")
    if neg.stderr_tail:
        r4.log("container stderr tail: " + " | ".join(neg.stderr_tail[-4:]))
    if neg_real:
        r4.log(
            "FAIL: a genuine reply arrived through a dead endpoint => the env contract was IGNORED."
        )
    elif not neg_backend_failed:
        r4.log(
            "FAIL: the negative neither replied nor evidenced a reach-and-fail; USED is unproven."
        )
    else:
        r4.log(
            "PASS-evidence: the negative reached the INJECTED dead endpoint and failed to connect "
            "(so the injected env drove the endpoint, not a baked-in default)."
        )
    facts["negative"] = _reply_facts(neg)

    facts["ended_at"] = _utcnow()
    overall = all(r.passed for r in reqs)
    return overall, reqs, facts


# Markers that a "completed" turn is actually a backend connection failure surfaced as agent text,
# NOT a genuine model generation. Hermes gracefully returns stop_reason=end_turn with an error
# notice when it cannot reach the endpoint, so the raw (outcome, stop_reason) pair is NOT enough to
# tell a real reply from a reached-a-dead-endpoint failure -- the discriminator below is required.
_FAILURE_MARKERS = (
    "connection error",
    "connection refused",
    "api call failed",
    "failed after",
    "retries",
    "cannot connect",
    "timed out",
)


def _backend_failed(result) -> bool:
    """True if the trail evidences a failure to reach the (injected) model endpoint."""
    text = result.text.strip().lower()
    stderr = " ".join(result.stderr_tail).lower()
    haystack = text + " || " + stderr
    return any(marker in haystack for marker in _FAILURE_MARKERS)


def _is_real_reply(result) -> bool:
    """A GENUINE model generation: a completed end_turn with non-error agent text.

    Crucially this rejects the case where the agent reached its (injected) endpoint, failed to
    connect, and surfaced that failure as end_turn text -- which is exactly what the negative
    control produces, and exactly what proves the env contract is USED (a dead endpoint => a
    failure, not a reply from some baked-in default).
    """
    return (
        result.outcome == "completed"
        and result.stop_reason == "end_turn"
        and bool(result.text.strip())
        and not _backend_failed(result)
    )


def _reply_facts(result) -> dict:
    return {
        "outcome": result.outcome,
        "stop_reason": result.stop_reason,
        "update_count": result.update_count,
        "text": result.text.strip()[:200],
        "real_reply": _is_real_reply(result),
        "backend_failed": _backend_failed(result),
    }


def write_record(overall: bool, reqs: list[Req], facts: dict) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# S1 Entry Gate — the containerized boundary",
        "",
        f"- Result: **{'PASS' if overall else 'FAIL'}**",
        f"- Image: `{facts.get('image')}`",
        f"- Smoke model: `{facts.get('model')}`",
        f"- Started: {facts.get('started_at')}  Ended: {facts.get('ended_at', 'n/a')}",
        "",
        "The gate proves what S0 deferred: the image builds, the ACP adapter is present in-image,",
        "a full ACP round-trip crosses the container boundary, and the injected provider env",
        "contract is not merely received but USED (a dead endpoint must fail — negative control).",
        "",
        "Raw runner-side ACP transcripts (ground truth for R3/R4): "
        "`records/entry-gate/pos-transcript.log`, `records/entry-gate/neg-transcript.log`.",
        "",
        "## Requirements",
        "",
        "| Req | Requirement | Result |",
        "|---|---|---|",
    ]
    for r in reqs:
        lines.append(f"| {r.key} | {r.title} | **{r.status}** |")
    lines.append("")
    for r in reqs:
        lines.append(f"### {r.key} — {r.title}: {r.status}")
        lines.append("")
        lines.append("```")
        lines.extend(r.lines)
        lines.append("```")
        lines.append("")
    if facts.get("positive") or facts.get("negative"):
        lines.append("## Env-contract differential (R4 evidence)")
        lines.append("")
        lines.append(
            "| control | endpoint | outcome | stop_reason | genuine reply? | backend failed? |"
        )
        lines.append("|---|---|---|---|---|---|")
        pos = facts.get("positive", {})
        neg = facts.get("negative", {})
        lines.append(
            f"| positive | host ollama | {pos.get('outcome')} | {pos.get('stop_reason')} | "
            f"{pos.get('real_reply')} | {pos.get('backend_failed')} |"
        )
        lines.append(
            f"| negative | dead endpoint | {neg.get('outcome')} | {neg.get('stop_reason')} | "
            f"{neg.get('real_reply')} | {neg.get('backend_failed')} |"
        )
        lines.append("")
        lines.append(f"positive reply text: `{pos.get('text', '')}`")
        lines.append("")
        lines.append(f"negative reply text: `{neg.get('text', '')}`")
        lines.append("")
    RECORD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="S1 entry gate")
    parser.add_argument("--image", default=HERMES_BARE_IMAGE)
    parser.add_argument("--model", default=SMOKE_MODEL_ID)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    overall, reqs, facts = gate(args.image, args.model, args.skip_build)
    write_record(overall, reqs, facts)

    print(f"\nEntry gate: {'PASS' if overall else 'FAIL'}  (record: {RECORD})")
    for r in reqs:
        print(f"  {r.key:14s} {r.status}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
