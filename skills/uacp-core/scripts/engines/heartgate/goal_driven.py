"""The goal-driven lifecycle track (A3.3 extraction from the Heartgate god-class).

The cohesive cluster implementing the second lifecycle track (ADR-0016): track
resolution (run/triage), goal binding + checkpoint counting, the convergence-budget
gate, the checkpoint-manifest loader + per-entry structural check, and the
goal-driven checkpoint/closure coherence gates. Carved out of the ``Heartgate``
god-class (design/graph-engine nodes 30/31, seam #6) as free functions taking the
gate instance (``hg``) for the state + sibling helpers they read. The hub keeps thin
delegating methods so the orchestrator, the adaptive gates, and the tests that drive
these directly are all unaffected; intra-cluster calls route through ``hg._x`` (the
delegations), so each function body is AST-identical to the original method (only
``self`` -> ``hg``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from engines.io import loaders as io_loaders

from .validators.helpers import _is_safe_run_id

if TYPE_CHECKING:
    from .heartgate import Heartgate

try:
    import yaml
except ImportError:  # pragma: no cover - Hermes ships with PyYAML in normal use.
    yaml = None  # type: ignore[assignment]


def run_track(hg: Heartgate, run_id: str) -> str:
    """Read a run's track from its manifest (state/runs/{run_id}.yaml).

    This is the ONLY seam by which Heartgate learns whether a run is on the
    goal-driven track. It is called from the goal-driven gates (the PROPOSE
    convergence-budget gate, the convergence cap, and the EXECUTE->VERIFY
    checkpoint relaxation). A standard-track transition DOES reach this read
    at those phase pairs, but it is a fail-safe, behavior-NEUTRAL read: it
    resolves to "standard" and every new behavior is strictly behind the
    ``== "goal-driven"`` branch, so the standard path stays byte-identical to
    before (the read returns "standard" and the gate proceeds exactly as it
    did, with no new blocker, warning, or side effect).

    Fail-safe: a missing/garbled manifest, or one that does not validate,
    resolves to ``"standard"`` (the default) — an autonomous-safety gate must
    not *itself* hard-fail a transition because the manifest could not be
    read; absent positive evidence of the goal-driven track, no new behavior
    fires. (The manifest's own existence/validity is enforced elsewhere.)
    """
    if not _is_safe_run_id(run_id):
        return "standard"
    try:
        from engines.io.loaders import load_manifest

        loaded = load_manifest(hg.uacp_root, run_id)
        if loaded.error is not None or loaded.value is None:
            return "standard"
        model = loaded.value.model
        if model is not None:
            return str(getattr(model, "track", "standard") or "standard")
        # Tolerate a manifest the strict schema rejected: read the raw track.
        raw = loaded.value.raw
        return str(raw.get("track") or "standard") if isinstance(raw, Mapping) else "standard"
    except Exception:
        return "standard"


def triage_track(hg: Heartgate, run_id: str) -> str:
    """Read the run's TRACK as decided by the TRIAGE artifact (authoritative).

    Council M-2: the manifest's ``track`` is set by the worker on its own
    manifest — a worker could self-select ``goal-driven`` to swap the
    deterministic PIV-artifact gate for the (relaxed) checkpoint-manifest
    gate. TRIAGE is where the track is *decided* (the mechanical
    specifiable-artifact test), so the TRIAGE artifact is the authority. This
    reads the ``track`` declared on the triage artifact at
    ``proposals/{run_id}-triage*.yaml`` (the same glob Heartgate's
    phase_exit_invariants use to locate it).

    Returns the triage ``track`` as a string, defaulting to ``"standard"``
    when the triage artifact is absent / unreadable / declares no track —
    i.e. a run is treated as goal-driven by TRIAGE ONLY on positive evidence.
    Never raises. (The FIRST matching triage artifact is consulted; the glob
    is normally singular.)
    """
    if not _is_safe_run_id(run_id):
        return "standard"
    try:
        from engines.io.loaders import glob_in_workspace
    except Exception:
        return "standard"
    try:
        matches = sorted(
            glob_in_workspace(hg.uacp_root, f"proposals/{run_id}-triage*.yaml"),
            key=lambda p: p.name,
        )
    except Exception:
        return "standard"
    if yaml is None:
        return "standard"
    for path in matches:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(raw, Mapping):
            return str(raw.get("track") or "standard") or "standard"
    return "standard"


def run_goal_id(hg: Heartgate, run_id: str) -> str:
    """Read a run's goal_id from its manifest (state/runs/{run_id}.yaml).

    Mirrors :meth:`_run_track`'s fail-safe manifest read: a missing/garbled/
    invalid manifest resolves to ``""`` (no positive goal binding) rather than
    raising. Used by the goal-driven closure gate to bind the promoted final
    checkpoint to the run's goal.
    """
    if not _is_safe_run_id(run_id):
        return ""
    try:
        from engines.io.loaders import load_manifest

        loaded = load_manifest(hg.uacp_root, run_id)
        if loaded.error is not None or loaded.value is None:
            return ""
        model = loaded.value.model
        if model is not None:
            return str(getattr(model, "goal_id", "") or "")
        raw = loaded.value.raw
        return str(raw.get("goal_id") or "") if isinstance(raw, Mapping) else ""
    except Exception:
        return ""


def goal_checkpoint_count(hg: Heartgate, goal_id: str) -> int:
    """Count gate: CHECKPOINT ledger entries across the goal's whole run-chain.

    A goal can span a CHAIN of runs (Task 3): "roll back to a checkpoint" is
    realized as launching a new forward run under the same persistent goal.
    So the convergence cap counts CHECKPOINT entries across ALL runs sharing
    the ``goal_id``.

    Council M-1 (autonomous-safety): the chain is enumerated by scanning the
    RUN MANIFESTS on disk (``state/runs/*.yaml``), NOT the run registry. The
    manifest's ``goal_id`` is the AUTHORITATIVE binding — it is what the
    per-run goal-driven gates read (:meth:`_run_track` / :meth:`_run_goal_id`)
    and what the registry writer is cross-checked against. The registry, by
    contrast, is self-declared and need not be complete: an executor can spawn
    a forward run that never registers (or registers under a different
    ``goal_id``), which would let a registry-based count UNDERcount and reset
    the budget per run -> an unbounded loop. Counting by manifest closes both
    "didn't register" and "registered under a different goal_id": every run
    whose MANIFEST declares this ``goal_id`` contributes its CHECKPOINT
    entries, regardless of registry presence.

    Never raises: an unreadable manifest/ledger contributes zero rather than
    crashing the gate (a fail-safe count, like the rest of the goal-driven
    path). A manifest the strict schema rejects still has its raw ``goal_id``
    consulted, so a structurally-odd-but-bound run is still counted.
    """
    if not goal_id:
        return 0
    try:
        from engines.io.loaders import glob_in_workspace, load_manifest
    except Exception:
        return 0
    total = 0
    seen: set[str] = set()
    try:
        manifests = glob_in_workspace(hg.uacp_root, "state/runs/*.yaml")
    except Exception:
        return 0
    for manifest_path in manifests:
        rid = manifest_path.stem  # filename sans .yaml is the run_id
        if not _is_safe_run_id(rid) or rid in seen:
            continue
        seen.add(rid)
        # Authoritative binding: this run is in the chain iff its MANIFEST
        # goal_id equals goal_id. Load tolerantly (never raise).
        try:
            loaded = load_manifest(hg.uacp_root, rid)
        except Exception:
            continue
        if loaded.error is not None or loaded.value is None:
            continue
        model = loaded.value.model
        if model is not None:
            run_goal = str(getattr(model, "goal_id", "") or "")
        else:
            raw = loaded.value.raw
            run_goal = str(raw.get("goal_id") or "") if isinstance(raw, Mapping) else ""
        if run_goal != goal_id:
            continue
        ledger_path = hg.governed_root / "state" / "gate-ledger" / f"{rid}.jsonl"
        if not ledger_path.exists():
            continue
        try:
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if str(rec.get("gate") or "") == "CHECKPOINT":
                    total += 1
        except Exception:
            continue
    return total


def load_convergence_budget(hg: Heartgate, run_id: str):
    """Load + validate the PROPOSE convergence-budget; returns ``(budget, error)``.

    Adapter (A2): the load/validate logic lives in
    :func:`engines.io.loaders.load_convergence_budget` (the Loaded contract);
    this returns the gate's ``(budget, error)`` tuple. The yaml-None guard
    stays here — core tolerates a missing PyYAML; the io layer hard-imports it.
    """
    if yaml is None:
        return None, "convergence_budget gate requires PyYAML"
    result = io_loaders.load_convergence_budget(hg.uacp_root, run_id)
    return result.value, result.error


def validate_convergence_budget_gate(
    hg: Heartgate, artifact: Mapping[str, Any], blockers: list[str]
) -> None:
    """PROPOSE->PLAN: a goal-driven run MUST declare a convergence budget,
    and its manifest track MUST match the TRIAGE decision.

    ADR-0016 R2: an autonomous goal-driven run (``claude -p``, cron) has no
    operator to sign off, so without a declared+enforced bound it loops
    forever. At PROPOSE->PLAN, when (and ONLY when) the run's track is
    ``goal-driven``, the PROPOSE convergence-budget artifact must exist and
    carry a positive ``max_checkpoints``. Standard runs skip this entirely —
    the track is read from the manifest behind the goal-driven branch, so
    the standard PROPOSE->PLAN path is unchanged.

    Council M-2 (un-forge the track): the manifest ``track`` is set by the
    worker, so a worker could self-select ``goal-driven`` to swap the
    deterministic PIV-artifact gate for the relaxed manifest gate. TRIAGE is
    the authority for the track decision. So when the manifest claims
    ``goal-driven``, the TRIAGE artifact's ``track`` (default ``standard``
    if absent) must ALSO be ``goal-driven`` — else fail CLOSED (a worker
    cannot self-relax the track). Still fully behind the goal-driven branch;
    the standard path is untouched.
    """
    if (
        str(artifact.get("from_phase") or "") != "propose"
        or str(artifact.get("to_phase") or "") != "plan"
    ):
        return
    run_id = str(artifact.get("run_id") or "")
    # TRACK GATE: read the manifest only after the phase guard, and only act
    # on goal-driven. A standard run returns here before any budget logic.
    if hg._run_track(run_id) != "goal-driven":
        return
    if not _is_safe_run_id(run_id):
        blockers.append("convergence_budget gate requires a valid run_id")
        return
    # Council M-2: the manifest track must match the TRIAGE decision. A
    # manifest that claims goal-driven over a triage artifact that did NOT
    # decide goal-driven is a self-relaxation -> fail closed.
    triage_track = hg._triage_track(run_id)
    if triage_track != "goal-driven":
        blockers.append(
            f"track mismatch: run manifest declares track 'goal-driven' but the "
            f"TRIAGE artifact decided track '{triage_track}' "
            "(proposals/{run_id}-triage*.yaml is authoritative; a worker may not "
            "self-select the goal-driven track to relax the PIV-artifact gate)".replace(
                "{run_id}", run_id
            )
        )
        return
    _budget, error = hg._load_convergence_budget(run_id)
    if error is not None:
        blockers.append(error)


def load_checkpoint_manifest(hg: Heartgate, run_id: str) -> list[Mapping[str, Any]]:
    """Read the run's gate: CHECKPOINT ledger records (raw, in ledger order).

    Adapter (A2): the ledger read lives in
    :func:`engines.io.loaders.load_checkpoint_manifest` (never raises). The
    run_id-safety guard stays here — an unsafe id yields no records.
    """
    if not _is_safe_run_id(run_id):
        return []
    return io_loaders.load_checkpoint_manifest(hg.uacp_root, run_id)


def validate_checkpoint_entry(hg: Heartgate, entry: Any, blockers: list[str]) -> None:
    """Structural claim=>evidence check for an in-EXECUTE checkpoint (ADR-0016).

    The goal-driven track records each EXECUTE iteration as a checkpoint
    manifest entry (gate-ledger ``gate: "CHECKPOINT"``). The manifest is NOT
    an honor system: a checkpoint's ``evidence`` must reference a real,
    governed-root-contained artifact — not a prose sentence, not a missing
    path, not a path that escapes the root. This is the same
    no-self-attestation rule Heartgate applies to other gate-ledger evidence,
    applied at the checkpoint boundary.

    Reuses :meth:`_artifact_path_exists` (the existing governed-root
    containment + existence helper) so the containment matches the rest of
    Heartgate — no hand-rolled path logic. A missing/empty evidence ref or a
    ref that escapes the governed root or does not resolve to a real file is
    a BLOCKER.

    Note: this validates the structural evidence coupling only. Wiring the
    checkpoint into the transition/gate flow (so it substitutes for PIV) is
    a later task; this method is exercised in isolation.
    """
    checkpoint_id = str(getattr(entry, "checkpoint_id", "") or "unknown")
    evidence = str(getattr(entry, "evidence", "") or "")
    if not evidence.strip():
        blockers.append(
            f"checkpoint {checkpoint_id}: evidence is required (no self-attestation — "
            "a checkpoint claim must reference a real artifact)"
        )
        return
    # Reuse the governed-root containment + existence helper: an evidence ref
    # that escapes the root or does not resolve to an existing file is not a
    # real artifact and cannot back the checkpoint's claim.
    if not hg._artifact_path_exists(evidence):
        blockers.append(
            f"checkpoint {checkpoint_id}: evidence artifact not found or escapes "
            f"governed root: {evidence}"
        )


def validate_goal_driven_checkpoint_gate(hg: Heartgate, run_id: str, blockers: list[str]) -> bool:
    """Validate a goal-driven run's in-EXECUTE checkpoint manifest (ADR-0016).

    Returns ``True`` iff the manifest is COHERENT — i.e. it may substitute for
    the deterministic PIV/findings-clearing artifacts at EXECUTE->VERIFY.
    "Coherent" means ALL of:

      * the manifest is non-empty (there is at least one ``gate: CHECKPOINT``
        record to substitute for the PIV/checkpoint artifacts);
      * EVERY record, once its ledger ENVELOPE is stripped (``gate``/``ts``
        and any non-payload key — ``run_id`` is itself a CheckpointEntry
        field and is kept), validates as a :class:`CheckpointEntry`
        (``extra="forbid"``) — a malformed/extra-field record is incoherent;
      * EVERY entry's ``evidence`` references a real governed-root-contained
        artifact (:meth:`_validate_checkpoint_entry` — the structural
        no-self-attestation / no-fabrication rule);
      * the total recorded checkpoint count does NOT exceed the convergence cap
        (checked post-loop with strict ``>`` against the already-recorded total
        — exactly ``max_checkpoints`` records PASSES; more BLOCKS);
      * the FINAL entry's verdict is ``keep`` — a dangling ``roll_back`` /
        ``restart`` means the run has not converged and must not promote.

    Any failure appends a blocker and returns ``False``. This method is only
    ever reached behind the goal-driven track gate in
    :meth:`_validate_adaptive_execute_evidence_gate`; it does not itself read
    the track.
    """
    from pydantic import ValidationError

    from engines.domain.checkpoint import CheckpointEntry

    records = hg._load_checkpoint_manifest(run_id)
    if not records:
        blockers.append(
            "goal-driven execute->verify: checkpoint manifest is empty "
            "(no gate: CHECKPOINT records to substitute for the PIV/execution "
            "evidence — the run has produced no governed checkpoint)"
        )
        return False

    coherent = True
    entries: list[CheckpointEntry] = []
    goal_id_seen: str | None = None
    # The ledger envelope keys the writer stamps that are NOT CheckpointEntry
    # payload fields. ``run_id`` IS a CheckpointEntry field, so it is kept.
    payload_fields = set(CheckpointEntry.model_fields)
    for idx, rec in enumerate(records, start=1):
        cid = str(rec.get("checkpoint_id") or f"#{idx}")
        # Envelope-strip: keep only valid CheckpointEntry payload keys so the
        # extra="forbid" model validates the PAYLOAD, not the envelope.
        payload = {k: v for k, v in rec.items() if k in payload_fields}
        try:
            entry = CheckpointEntry(**payload)
        except ValidationError as exc:
            first = exc.errors()[0] if exc.errors() else {}
            detail = first.get("msg") or str(exc)
            loc = ".".join(str(p) for p in (first.get("loc") or [])) or "?"
            blockers.append(
                f"goal-driven checkpoint manifest: checkpoint {cid} is malformed "
                f"(CheckpointEntry validation failed at {loc}: {detail})"
            )
            coherent = False
            continue
        entries.append(entry)
        if goal_id_seen is None and entry.goal_id:
            goal_id_seen = entry.goal_id
        # Structural claim=>evidence (no self-attestation / no-fabrication).
        before = len(blockers)
        hg._validate_checkpoint_entry(entry, blockers)
        if len(blockers) != before:
            coherent = False

    # Cap: block iff the total recorded checkpoint count for this goal EXCEEDS
    # max_checkpoints (strict >). A manifest with EXACTLY max_checkpoints
    # entries is at-budget and PASSES; max_checkpoints+1 BLOCKS.
    # This is the LIVE cap path (council MINOR+cleanup removed the dead
    # _validate_convergence_cap pre-append helper): a post-hoc check on an
    # already-recorded total, so it uses strict > (not >=) against the total
    # the manifest scan returns for this goal's whole run-chain.
    if goal_id_seen:
        budget, budget_error = hg._load_convergence_budget(run_id)
        if budget_error is not None or budget is None:
            blockers.append(
                budget_error or "convergence cap: goal-driven run requires a convergence_budget"
            )
            coherent = False
        else:
            count = hg._goal_checkpoint_count(goal_id_seen)
            if count > budget.max_checkpoints:
                blockers.append(
                    f"convergence_budget exhausted: goal '{goal_id_seen}' has {count} "
                    f"checkpoint(s), cap is max_checkpoints={budget.max_checkpoints}; "
                    "the manifest exceeds the convergence budget "
                    "(the run must converge or escalate, not loop)"
                )
                coherent = False

    # The manifest must converge on a keep: a dangling roll_back/restart final
    # verdict means the probe was discarded — there is nothing to promote.
    if entries and entries[-1].verdict != "keep":
        blockers.append(
            "goal-driven checkpoint manifest: final checkpoint verdict is "
            f"'{entries[-1].verdict}' (a dangling roll_back/restart has not "
            "converged on a keep — there is no result to promote to VERIFY)"
        )
        coherent = False

    return coherent


def validate_goal_driven_closure_gate(hg: Heartgate, run_id: str, blockers: list[str]) -> bool:
    """Gate a goal-driven run's CLOSURE on manifest coherence (ADR-0016 O5).

    A goal-driven run's checkpoints are disposable probes until one SATISFIES
    the goal; that satisfying checkpoint is *promoted to result* and the run
    closes. This gate is what lets the run close: it requires the run's
    checkpoint manifest to be COHERENT *and* the final (promoted) checkpoint's
    evidence to be BOUND TO THE GOAL.

    "Manifest coherence at closure" is NOT a lower bar — it ADDS to the shared
    standard closure invariants (the computed engines, no-fabrication,
    containment), which continue to fire unchanged for goal-driven runs (this
    gate does not touch them). It layers these REQUIREMENTS on top:

      * the manifest is COHERENT per :meth:`_validate_goal_driven_checkpoint_gate`
        — every CHECKPOINT entry parses, each entry's ``evidence`` references a
        real governed-root-contained artifact (the no-self-attestation /
        no-fabrication / containment rule), no keep is over the convergence
        cap, AND the FINAL entry's verdict is ``keep`` (no dangling roll_back /
        restart — i.e. (a) final keep and (b) no dangling non-keep are the same
        convergence requirement, enforced there); AND
      * the FINAL (promoted) checkpoint's evidence is BOUND TO THE GOAL: its
        ``goal_id`` equals the run manifest's ``goal_id``. A final keep whose
        evidence belongs to a DIFFERENT goal is not a result for THIS goal and
        must not close the run. (The final entry's evidence EXISTENCE is already
        enforced by the coherence pass above; this adds the goal binding.)

    DRY: the coherence layer is the SAME Task-6 helper used at EXECUTE->VERIFY
    (:meth:`_validate_goal_driven_checkpoint_gate`); this gate reuses it rather
    than re-deriving "coherent", then layers only the goal-binding requirement
    the closure boundary adds. Returns ``True`` iff coherent AND goal-bound;
    any failure appends a blocker and returns ``False``.
    """
    coherent = hg._validate_goal_driven_checkpoint_gate(run_id, blockers)

    # The promoted result is the FINAL checkpoint. Its evidence must be bound
    # to the run's goal — a final keep recorded under a different goal_id is
    # not a result for THIS run's goal. (Existence/containment of that evidence
    # is enforced by the coherence pass above; this adds the goal binding.)
    final = hg._final_checkpoint_entry(run_id)
    run_goal_id = hg._run_goal_id(run_id)
    if final is not None and run_goal_id:
        final_goal_id = str(getattr(final, "goal_id", "") or "")
        if final_goal_id != run_goal_id:
            blockers.append(
                "goal-driven closure: final checkpoint evidence is not bound to "
                f"the run's goal (final checkpoint goal_id '{final_goal_id}' != run "
                f"goal_id '{run_goal_id}' — the promoted result must satisfy THIS "
                "run's goal)"
            )
            return False
    return coherent


def final_checkpoint_entry(hg: Heartgate, run_id: str):
    """Parse the LAST gate: CHECKPOINT manifest record into a CheckpointEntry.

    Returns the final entry (or ``None`` if the manifest is empty / the final
    record does not validate). Reuses :meth:`_load_checkpoint_manifest` (the
    same raw-record reader the coherence gate uses) and the same envelope-strip
    rule, so the "final entry" this sees is exactly the one the coherence gate
    validated. Never raises.
    """
    from pydantic import ValidationError

    from engines.domain.checkpoint import CheckpointEntry

    records = hg._load_checkpoint_manifest(run_id)
    if not records:
        return None
    payload_fields = set(CheckpointEntry.model_fields)
    payload = {k: v for k, v in records[-1].items() if k in payload_fields}
    try:
        return CheckpointEntry(**payload)
    except ValidationError:
        return None
