"""Cell definitions as data.

A *cell* is one row of the benchmark matrix (40-benchmark): an agent runtime baked into a docker
image, driven against a model reached through a standard provider **env contract** (10-topology
sec. 3): ``OPENAI_BASE_URL`` + ``OPENAI_API_KEY`` (dummy for local) + a **REQUIRED, pinned**
``model_id``. The pinned ``model_id`` is non-optional by design: a base URL selects the *server*,
not the *model*, and a multi-model host like ollama would let a default drift turn the +/-UACP
ablation into a silent model confound. Constructing a cell without a ``model_id`` is refused.

``uacp`` is carried as a field but is unused until S2 (the +UACP cell bakes the plugin surface).

stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass

# The env-contract variable names the cell image's entrypoint consumes (images/hermes/entrypoint.sh
# renders HERMES_HOME/config.yaml from exactly these three, then execs `hermes acp`).
ENV_BASE_URL = "OPENAI_BASE_URL"
ENV_API_KEY = "OPENAI_API_KEY"
ENV_MODEL_ID = "UACP_MODEL_ID"

# From inside a Docker Desktop (macOS) container the host ollama is reachable here.
HOST_OLLAMA_OPENAI_URL = "http://host.docker.internal:11434/v1"

# Egress modes (10-topology "Per-cell egress policy"). Advisory in S1 (enforcement is later work),
# but recorded so an undeclared egress is a finding rather than a silent default.
EGRESS_HOST_MODEL = "host-model"  # local cell: host model endpoint only
EGRESS_PROVIDER_API = "provider-api"  # cloud cell: one provider API only
# S1 runs on Docker's default bridge — the declared policy is NOT yet enforced at the container
# boundary, and every run record must say so (a reader of meta.json must not assume containment
# that does not exist). Probed 2026-07-18: `docker network create --internal` blocks host-gateway
# too on Docker Desktop, so enforcement needs the dual-network proxy-sidecar pattern → S2 (50-plan).
# S2 flips this constant when the sidecar lands; until then it is the honesty bit, not a knob.
EGRESS_ENFORCED = False


@dataclass(frozen=True)
class Cell:
    """One benchmark cell. Immutable so a sweep cannot mutate a cell mid-run."""

    name: str
    image: str
    model_id: str
    base_url: str = HOST_OLLAMA_OPENAI_URL
    api_key: str = "ollama"  # dummy; local ollama ignores it
    workspace_mount: str = "/workspace"
    egress: str = EGRESS_HOST_MODEL
    uacp: bool = False  # S2: toggles the in-image plugin surface

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Cell.name is required")
        if not self.image:
            raise ValueError("Cell.image is required")
        # The pinned model_id is load-bearing (10-topology sec. 3): refuse a cell without one.
        if not self.model_id or not self.model_id.strip():
            raise ValueError(
                f"Cell {self.name!r} has no model_id; a pinned model_id is required by the env "
                "contract (a base URL selects the server, not the model)."
            )

    def render_env(self) -> dict[str, str]:
        """The provider env contract injected into the container (docker run -e ...)."""
        return {
            ENV_BASE_URL: self.base_url,
            ENV_API_KEY: self.api_key,
            ENV_MODEL_ID: self.model_id,
        }


# The image tag the entry gate builds and the smoke run consumes.
HERMES_BARE_IMAGE = "proving-ground/hermes-bare:s1"

# Smoke-tier model. mike's preference 2026-07-18: same family as the scored qwen3.6:35b-a3b.
# Probe-verified: qwen3.5:4b reports 262K context (>= Hermes's hard 64K floor, an S0 finding) and
# passes tool-calling. See design/proving-ground/40-benchmark.md for the smoke-tier criteria.
SMOKE_MODEL_ID = "qwen3.5:4b"


def hermes_bare(model_id: str = SMOKE_MODEL_ID, image: str = HERMES_BARE_IMAGE) -> Cell:
    """The S1 automated-lane floor cell: Hermes, host ollama via the env contract, UACP off."""
    return Cell(
        name="hermes-bare",
        image=image,
        model_id=model_id,
        egress=EGRESS_HOST_MODEL,
        uacp=False,
    )
