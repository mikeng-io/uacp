"""Deferral-completeness validator for UACP runs (codes prefixed ``DF_``).

Enforces the kernel's "no silently-dropped risks" expectation: every item a run
defers (a risk / piece of work pushed to a later phase) must be FULLY specified
— it must name an owner, the residual risk it carries, and the obligation that
carries it forward — and a deferred item declared earlier must still be
accounted for at closure. A half-specified deferral is how a real risk leaks out
of governance unowned.

Grounding — where deferred items actually live, and what they MUST carry
========================================================================

UACP has no single canonical ``DeferredItem`` schema; the concept appears in
several loosely-typed places (see ``engines/domain/deferral.py``). This engine
reads deferred items from the two locations a *run* actually records them:

1. **The run manifest's top-level ``deferred_items`` list** — declared in
   ``config/state.yaml`` ``run_state_schema.deferred_items`` (``type: list``,
   ``item_type: map``). This is the run's own durable record of carried risk
   (the bootstrap manifest in ``config/state.yaml`` populates exactly this).
2. **The run's closure / lessons artifact** — the RESOLVE artifact registered in
   ``manifest.artifacts`` under ``lessons`` (also accepted: ``resolution`` /
   ``learning``). The ``adaptive_resolve_closure_gate`` in
   ``config/phase-transitions.yaml`` requires RESOLVE to *preserve residual
   risks / deferred items* (``block_when: residual_risk_or_deferred_item_dropped``),
   so the closure artifact is where deferrals must land at the end of the run.
   We read a ``deferred_items`` list out of that artifact if present.

**Required fields per item** (the union the schemas actually name — not invented):

* ``owner`` — ``config/artifact-schemas.yaml`` ``evidence_disposition.
  assumptions_dispositions.deferred.requires: [owner, next_phase_obligation]``;
  also ``config/evidence-clusters.yaml`` ("deferred items have owner/...").
* ``residual_risk`` — ``config/evidence-clusters.yaml`` ("warnings/deferred items
  have owner/residual_risk/next_phase_acceptance").
* ``next_phase_obligation`` — ``config/artifact-schemas.yaml`` ``deferred.requires``
  (the carry-forward obligation). The schema's literal field name is
  ``next_phase_obligation``; this engine uses that exact name.

Required-ness uses **key presence**, not truthiness: a field is "present" when
its key exists with a non-empty value. A key that is absent OR whose value is
empty / blank / null is treated as MISSING — matching how the schemas phrase the
requirement ("deferred items HAVE owner/..."). An item with no usable identity is
addressed by its 1-based index so the violation still points somewhere concrete.

Codes
=====

* ``DF_DEFERRAL_MISSING_OWNER`` — a deferred item lacks ``owner``.
* ``DF_DEFERRAL_MISSING_RESIDUAL_RISK`` — a deferred item lacks ``residual_risk``.
* ``DF_DEFERRAL_MISSING_OBLIGATION`` — a deferred item lacks
  ``next_phase_obligation``.
* ``DF_DEFERRAL_DROPPED_AT_RESOLVE`` — the run is ``status == 'resolved'`` and an
  item present in the manifest's ``deferred_items`` (declared earlier in the run)
  has NO counterpart (matched by ``id``) in the closure/lessons artifact's
  ``deferred_items``. This is the cross-phase "carried-forward" check; it only
  fires when BOTH a closure artifact and an ``id`` exist to correlate on (see
  limits). If the closure artifact declares no ``deferred_items`` list at all
  while the manifest does, that is treated as a wholesale drop (every identified
  manifest item is dropped).

What this engine does NOT check (deliberate non-overlap + honest limits)
========================================================================

* It does NOT check artifact PRESENCE or ledger/state-history agreement — that is
  ``coherence`` (C2/C4) and ``evidence_completeness``. This engine inspects the
  CONTENT of each deferred item (per-item field completeness + carry-forward).
* **No deferrals ⇒ no-op.** If neither the manifest nor the closure artifact
  records any deferred item, the engine returns ``[]``. Absence of deferral data
  is not a finding (a run with nothing deferred is the common, healthy case).
* **DF_DROPPED needs identity to correlate.** Manifest deferred items WITHOUT an
  ``id`` cannot be matched against the closure set and are not reported as
  dropped (we never guess identity). Items with an ``id`` are matched on it.
* **Field *quality*.** A present field is checked for non-emptiness only, not for
  semantic adequacy of its text — that is a council concern.

Architecture: PURE of filesystem I/O. All disk reads go through :mod:`engines.io`
read-models; this module never raises — every failure mode becomes a
:class:`~engines.base.Violation` or a no-op. An empty result list means "clean".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engines.base import ENGINES, Violation
from engines.domain import DeferredItem
from engines.io import load_artifact, load_manifest
from engines.io.loaders import ManifestDoc

# Artifact-manifest keys under which a run registers its closure/lessons artifact
# (the RESOLVE record that must preserve deferred items). ``lessons`` is what the
# happy-path run registers; ``resolution`` / ``learning`` are the other RESOLVE
# slots declared in config/state.yaml run_state_schema.artifacts.
_CLOSURE_ARTIFACT_KEYS = ("lessons", "resolution", "learning")

# The fields each deferred item MUST carry, mapped to the code emitted when the
# field is missing. Names are taken verbatim from the schemas (see module docstring).
_REQUIRED_FIELDS: tuple[tuple[str, str], ...] = (
    ("owner", "DF_DEFERRAL_MISSING_OWNER"),
    ("residual_risk", "DF_DEFERRAL_MISSING_RESIDUAL_RISK"),
    ("next_phase_obligation", "DF_DEFERRAL_MISSING_OBLIGATION"),
)


def _v(code: str, message: str, severity: str = "block", **detail: Any) -> Violation:
    return Violation(code=code, severity=severity, message=message, detail=detail)


def _coerce_items(raw: Any) -> list[dict[str, Any]]:
    """Return the deferred-item mappings from a raw ``deferred_items`` value.

    Tolerant: a non-list yields ``[]``; non-mapping elements are dropped (we can
    only inspect fields on a mapping). Never raises.
    """
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _field_present(item: DeferredItem, field: str) -> bool:
    """True iff ``field`` is present AND carries a non-empty value.

    Uses ``model_fields_set`` / key presence so an ABSENT field is distinguished
    from one explicitly set; but a present-yet-empty value (``None`` / blank
    string / empty container) is still treated as MISSING, because the schemas
    phrase the requirement as the item *having* the field, not merely declaring
    the key. Extra (non-modelled) keys are honoured via the model's ``extra``.
    """
    # Pydantic v2: declared fields recorded in model_fields_set; extra="allow"
    # keys live in model_extra. Treat a key as present only if it is in one of
    # those AND its value is non-empty.
    in_declared = field in item.model_fields_set
    extra = item.model_extra or {}
    in_extra = field in extra
    if not in_declared and not in_extra:
        return False
    value = getattr(item, field, None) if in_declared else extra.get(field)
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict, tuple, set)) and len(value) == 0:
        return False
    return True


def _item_label(item: DeferredItem, index: int) -> str:
    """A stable human label for an item: its ``id`` if usable, else ``#<index>``."""
    iid = item.id
    if isinstance(iid, str) and iid.strip():
        return iid.strip()
    return f"#{index}"


def _check_item_fields(item: DeferredItem, label: str, source: str) -> list[Violation]:
    """Emit one violation per required field the item is missing."""
    out: list[Violation] = []
    for field, code in _REQUIRED_FIELDS:
        if not _field_present(item, field):
            out.append(
                _v(
                    code,
                    f"deferred item '{label}' in {source} lacks required field '{field}'",
                    deferred_item=label,
                    field=field,
                    source=source,
                )
            )
    return out


def _closure_artifact_rel(manifest: dict[str, Any]) -> str | None:
    """Return the first registered closure/lessons artifact path, or None."""
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    for key in _CLOSURE_ARTIFACT_KEYS:
        rel = artifacts.get(key)
        if isinstance(rel, str) and rel.strip():
            return rel.strip()
    return None


def validate_deferral_completeness(workspace: str | Path, run_id: str) -> list[Violation]:
    """Validate that every deferred item a run records is fully specified and that
    earlier-declared deferrals are carried into the run's closure. Returns a list
    of Violation (empty == clean). Never raises.
    """
    violations: list[Violation] = []
    try:
        root = Path(str(workspace)).resolve()
    except Exception as exc:
        return [_v("DF0_WORKSPACE_INVALID", f"workspace path invalid: {type(exc).__name__}: {exc}")]

    if not run_id or not isinstance(run_id, str):
        return [_v("DF0_RUN_ID_INVALID", f"run_id invalid: {run_id!r}")]

    loaded = load_manifest(root, run_id)
    if loaded.error is not None:
        return [_v("DF0_MANIFEST_MISSING", f"run manifest could not be loaded: {loaded.error}")]
    doc: ManifestDoc = loaded.value
    manifest = doc.raw

    status = manifest.get("status")

    # 1) Deferred items recorded directly on the manifest.
    manifest_raw_items = _coerce_items(manifest.get("deferred_items"))
    manifest_items: list[tuple[DeferredItem, str]] = []
    for idx, raw in enumerate(manifest_raw_items, start=1):
        item = DeferredItem.model_validate(raw)
        label = _item_label(item, idx)
        manifest_items.append((item, label))
        violations.extend(_check_item_fields(item, label, "manifest deferred_items"))

    # 2) Deferred items recorded in the run's closure / lessons artifact.
    closure_rel = _closure_artifact_rel(manifest)
    closure_present = False
    closure_ids: set[str] = set()
    closure_has_deferred_list = False
    if closure_rel is not None:
        art = load_artifact(root, closure_rel)
        if art.error is None and art.value is not None:
            closure_present = True
            if "deferred_items" in art.value:
                closure_has_deferred_list = True
            closure_raw_items = _coerce_items(art.value.get("deferred_items"))
            for idx, raw in enumerate(closure_raw_items, start=1):
                item = DeferredItem.model_validate(raw)
                label = _item_label(item, idx)
                violations.extend(
                    _check_item_fields(item, label, f"closure artifact '{closure_rel}'")
                )
                if isinstance(item.id, str) and item.id.strip():
                    closure_ids.add(item.id.strip())

    # 3) Cross-phase carry-forward: a resolved run must carry every IDENTIFIED
    #    manifest deferral into its closure artifact. Only computable when a
    #    closure artifact exists and the manifest item has an id to correlate on.
    if status == "resolved" and closure_present:
        for item, label in manifest_items:
            iid = item.id
            if not (isinstance(iid, str) and iid.strip()):
                continue  # no identity to correlate — never guessed as dropped
            if iid.strip() not in closure_ids:
                detail_note = (
                    "closure artifact declares no deferred_items list"
                    if not closure_has_deferred_list
                    else "id absent from closure deferred_items"
                )
                violations.append(
                    _v(
                        "DF_DEFERRAL_DROPPED_AT_RESOLVE",
                        f"deferred item '{label}' declared in the manifest is not "
                        f"carried into the closure artifact '{closure_rel}' "
                        f"({detail_note})",
                        deferred_item=label,
                        closure_artifact=closure_rel,
                    )
                )

    return violations


# Register this engine (guard against double-registration under alias imports).
if not any(name == "deferral_completeness" for name, _ in ENGINES):
    ENGINES.append(("deferral_completeness", validate_deferral_completeness))
