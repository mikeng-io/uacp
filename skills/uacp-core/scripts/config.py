"""UACP configuration resolver.

Loads the kernel-shipped default ``config/uacp.toml`` and (optionally) deep-merges
a project-local ``<project_root>/.uacp/config.toml`` override on top of it, then
validates the result into a typed :class:`UacpConfig`.

This module is purely additive: as of Slice 1 nothing in the kernel reads it yet.
It establishes the ``[paths]`` knob and a traversal-safe path resolver that later
slices build on.
"""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

from filesystem import _resolve_uacp_path
from pydantic import BaseModel, ConfigDict


class Paths(BaseModel):
    """Subdirectory names under the governed namespace root (``base``).

    Every field carries an inline default matching ``config/uacp.toml`` so a
    *partial* project override (e.g. only ``base``) still validates and leaves
    sibling fields at their defaults.

    ``extra="allow"`` preserves nested path subtables (e.g.
    ``[paths.bridge_artifacts]``, ``[paths.council_artifacts]``) that have no
    declared field above. Without it Pydantic v2 silently drops them — that is
    data loss, since bridge/council skills reference those paths.
    """

    model_config = ConfigDict(extra="allow")

    base: str = ".uacp"
    state: str = "state"
    proposals: str = "proposals"
    plans: str = "plans"
    executions: str = "executions"
    verification: str = "verification"
    resolutions: str = "resolutions"
    knowledge: str = "knowledge"
    config: str = "config.toml"


class UacpConfig(BaseModel):
    """Top-level UACP configuration.

    ``extra="allow"`` keeps the model forward-compatible: knob sections added in
    later slices (e.g. ``[bridges]``, ``[council]``) are retained rather than
    rejected during validation.
    """

    model_config = ConfigDict(extra="allow")

    paths: Paths = Paths()

    def resolve(self, root: Path, path_key: str, *parts: str) -> Path:
        """Resolve a path under the governed namespace, traversal-safely.

        Composes ``<paths.base>/<subdir>/<*parts>`` (where ``subdir`` is the
        ``[paths]`` field named ``path_key``) and resolves it under ``root`` via
        :func:`filesystem._resolve_uacp_path`, which rejects absolute paths,
        empty/``.``/``..`` segments, and symlink traversal.

        Raises:
            ValueError: if ``path_key`` is not a known ``[paths]`` field, or if
                the composed path would escape ``root``/``<paths.base>``.
        """
        if path_key not in type(self.paths).model_fields:
            known = ", ".join(sorted(type(self.paths).model_fields))
            raise ValueError(f"unknown paths key {path_key!r}; expected one of: {known}")
        subdir = getattr(self.paths, path_key)
        rel = Path(self.paths.base) / subdir
        for part in parts:
            rel = rel / part
        return _resolve_uacp_path(str(rel), root)


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into ``base``, returning a new dict.

    Leaf values in ``override`` win. Nested tables present in both are merged
    rather than wholesale-replaced, so a partial override preserves sibling
    defaults. ``base`` is not mutated.
    """
    result = dict(base)
    for key, value in override.items():
        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            result[key] = _deep_merge(existing, value)
        else:
            result[key] = value
    return result


def _default_toml_path() -> Path:
    """Path to the kernel-shipped default config (``<repo>/config/uacp.toml``)."""
    return Path(__file__).resolve().parents[3] / "config" / "uacp.toml"


def load_config(project_root: Path | None = None) -> UacpConfig:
    """Load UACP config: kernel default, deep-merged with an optional override.

    Reads the default ``config/uacp.toml``. If ``project_root`` is provided and
    ``<project_root>/.uacp/config.toml`` exists, that file is deep-merged on top
    (override wins on leaves; nested tables merged, not replaced). A missing
    override is not an error — the default-only config is valid.
    """
    with _default_toml_path().open("rb") as fh:
        merged: dict = tomllib.load(fh)

    if project_root is not None:
        override_path = Path(project_root) / ".uacp" / "config.toml"
        if override_path.exists():
            with override_path.open("rb") as fh:
                override = tomllib.load(fh)
            merged = _deep_merge(merged, override)

    return UacpConfig(**merged)


@lru_cache(maxsize=256)
def _cached_config(root_str: str, _mtime: float) -> UacpConfig:
    """Cache by (resolved root, override mtime). The ``_mtime`` arg is part of
    the cache key only — when ``.uacp/config.toml`` is created or edited its
    mtime changes, producing a fresh key and a re-parse, so a long-lived
    process never serves stale paths (council S2)."""
    return load_config(Path(root_str))


def clear_config_cache() -> None:
    """Drop the per-root config cache. Call between tests that mutate a
    project's ``.uacp/config.toml`` after a prior read (a conftest autouse
    fixture wires this up suite-wide once Slice 2's conftest change lands)."""
    _cached_config.cache_clear()


def get_config(root: Path) -> UacpConfig:
    """Config for ``root``, deep-merging ``<root>/.uacp/config.toml`` if present.

    Cached per resolved root *and* the override file's mtime so kernel readers
    do not re-parse TOML on every path lookup, yet a created/edited override is
    picked up without an explicit :func:`clear_config_cache` (council S2). The
    override always lives at the fixed bootstrap home ``<root>/.uacp/config.toml``
    regardless of ``[paths] base`` — ``base`` relocates runtime dirs only.
    """
    root_r = Path(root).resolve()
    override = root_r / ".uacp" / "config.toml"
    # Single stat() (no exists()-then-stat() TOCTOU): a missing or vanished
    # override keys as 0.0 rather than crashing a hot-path lookup on a race.
    try:
        mtime = override.stat().st_mtime
    except OSError:
        mtime = 0.0
    return _cached_config(str(root_r), mtime)


def base_dir(root: Path) -> Path:
    """The governed namespace root: ``<root>/<paths.base>`` (default ``.uacp``).

    ``paths.base`` is config-controlled (``.uacp/config.toml`` may override it),
    so containment is enforced: the resolved base must stay under ``root``. A
    base that escapes (e.g. ``"../foo"``) raises ``ValueError`` — fail closed,
    matching :meth:`UacpConfig.resolve`'s traversal semantics.
    """
    cfg = get_config(root)
    root_resolved = Path(root).resolve()
    candidate = (root_resolved / cfg.paths.base).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"paths.base {cfg.paths.base!r} escapes root {root_resolved}")
    return candidate


def dir_for(root: Path, path_key: str) -> Path:
    """Resolve a declared ``[paths]`` subdir under the governed base.

    ``path_key`` must be a declared field (unknown key raises ``ValueError`` so
    typos fail loud). The subdir *value* is config-controlled, so containment is
    enforced: the result must stay under the governed base — a traversing value
    raises ``ValueError`` (fail closed).
    """
    cfg = get_config(root)
    if path_key not in type(cfg.paths).model_fields:
        known = ", ".join(sorted(type(cfg.paths).model_fields))
        raise ValueError(f"unknown paths key {path_key!r}; expected one of: {known}")
    base = base_dir(root)
    candidate = (base / getattr(cfg.paths, path_key)).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"paths.{path_key} {getattr(cfg.paths, path_key)!r} escapes base {base}")
    return candidate
