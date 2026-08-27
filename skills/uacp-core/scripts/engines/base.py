"""Shared contract for computed Heartgate engines.

Every deterministic validator ("engine") in UACP shares ONE violation type and
registers itself in ONE registry, so a single sweep can run them all. Engines
are read-only consumers of the kernel's emitted state: given a ``workspace``
(UACP_ROOT) and a ``run_id`` they return a list of :class:`Violation` (empty ==
clean) and MUST NOT raise.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    """A single validation failure shared by every engine.

    code     — stable identifier (e.g. "C1_RUN_ID_MISMATCH").
    severity — "block" (run is incoherent) or "warn" (suspicious, not fatal).
    message  — human-readable, names exactly what disagreed.
    detail   — optional structured context for programmatic consumers.
    """

    code: str
    severity: str
    message: str
    detail: dict = field(default_factory=dict)

    def as_finding(self) -> dict:
        """The ONE structured serializer for a violation (register move M4 / D-09).

        Programmatic consumers were forced to re-parse the flattened
        ``f"{code}: {message}"`` strings the boundary emitted; ``detail`` — the
        "structured context for programmatic consumers" this dataclass already
        carries — was being destroyed at every flattening site. This method
        surfaces it instead, in ONE place, so every boundary that serializes
        findings (the transition payload, the closure decision, the MCP surface)
        shares a single shape and cannot re-diverge.

        ``path`` is the most useful single locator we can lift out of ``detail``
        without inventing a key: the first of ``path`` / ``target`` / ``artifact``
        that is set (else ``None``). The full ``detail`` is still returned intact.
        """
        detail = self.detail if isinstance(self.detail, dict) else {}
        path = detail.get("path") or detail.get("target") or detail.get("artifact")
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "detail": dict(detail),
            "path": path,
        }


# An engine validates one run: (workspace, run_id) -> violations. Never raises.
Engine = Callable[[Path, str], list[Violation]]

# Registry of (name, validate_fn). Populated as engines are added — engine
# modules append themselves on import (see engines/__init__.py).
ENGINES: list[tuple[str, Engine]] = []


def run_all_engines(workspace: str | Path, run_id: str) -> list[Violation]:
    """Run every registered engine over one run and aggregate the violations.

    Engines already never raise, but each call is defensively wrapped so that
    an unexpected failure in one engine cannot abort the sweep: it is converted
    into an ``ENGINE_CRASHED`` violation and the next engine still runs.
    """
    out: list[Violation] = []
    for name, engine in ENGINES:
        try:
            out.extend(engine(Path(str(workspace)), run_id))
        except Exception as exc:  # defensive: one engine must not break the sweep
            out.append(
                Violation(
                    code="ENGINE_CRASHED",
                    severity="block",
                    message=f"engine '{name}' raised unexpectedly: {type(exc).__name__}: {exc}",
                    detail={"engine": name},
                )
            )
    return out
