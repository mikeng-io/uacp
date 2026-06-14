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
