# UACP E2E acceptance — `runner:hermes`, Priority 1: PLUGIN CONFORMANCE (design nodes 11/13).
#
# The Hermes twin of ../Dockerfile. Same discipline, different install recipe: Hermes has no
# marketplace, so the user-real install is the symlink binding declared in
# `config/uacp.toml [runtime_bindings.hermes]` — `HERMES_ROOT/plugins/<adapter>` -> the repo's
# `runtime-adapters/hermes/plugins/<adapter>/` — plus `hermes plugins enable` (plugins are opt-in).
#
# WHY NO `FROM python:3.x`
# -----------------------
# The defect this harness exists to catch was an interpreter-floor defect: UACP core shipped PEP 695
# syntax (`class Loaded[T]`, 3.12+) while the Hermes venv is 3.11, so the plugin silently failed to
# load and was merely marked `error`. Pinning a base interpreter here would be choosing the
# environment instead of reproducing it. Hermes' own `install.sh` hardcodes `PYTHON_VERSION="3.11"`
# and builds its venv with `uv venv venv --python 3.11` (uv downloads that interpreter if absent), so
# the ONLY faithful thing to do is give it a bare OS and let its installer select the interpreter.
# `debian:bookworm-slim` carries no Python at all — whatever runs Hermes here is whatever Hermes
# chose, exactly as on a user's machine. (The proving-ground image at
# tools/proving-ground/images/hermes/ pins python:3.12-slim; that is a cell image, not a floor
# reproduction, and it must not be copied here.)
#
# NO WARMING, NO SHORTCUTS: no pre-resolved deps, no source mount standing in for an install, no
# cache priming. If the first real launch is broken, this test EXPOSES it. (Inherited from
# ../Dockerfile.)
FROM debian:bookworm-slim

# Only what a user needs to run Hermes' published installer. Hermes' install.sh bootstraps `uv`
# itself, and uv provisions the interpreter — so no Python is installed here on purpose.
# `xz-utils` is not a shortcut: install.sh unpacks its Node.js tarball with `tar` + `xz` and hard-
# fails without it (same reason tools/proving-ground/images/hermes/Dockerfile carries it).
# `jq` is a HARNESS tool (it parses Hermes' own JSON reports), in the same class as curl — it is not
# a UACP dependency and nothing under test is installed here.
#
# `xz-utils` and `libatomic1` are BASE-OS runtime libraries that `-slim` strips but any real machine
# has; they are not shortcuts. Hermes' installer untars its Node.js tarball with xz, and from
# v2026.8.27 it installs Node 26, whose binary links `libatomic.so.1` — without it `node --version`
# dies with "error while loading shared libraries" and the whole install aborts (exit 127). Supplying
# `build-essential` is likewise the installer's OWN stated requirement, not our shortcut: from
# v2026.8.27 it needs a C++ compiler for native Node modules (node-pty) and ABORTS without one,
# after trying `sudo apt install build-essential` itself — which fails here only because the
# container user has no sudo. Supplying it reproduces what that installer does on a real machine.
#
# `python3` is for NODE-GYP, not for Hermes. node-gyp shells out to a `python3` on PATH to configure
# native module builds, and without one `npm install` fails silently (no output, non-zero exit) and
# the installer aborts — from v2026.8.27 that npm step is fatal by design (upstream #85297) and
# `--skip-browser` does NOT skip it. This does NOT undo the no-Python-base rule above: Hermes still
# picks its own interpreter via uv, and the two are distinguishable — Debian bookworm ships python
# 3.11.2 while uv installs 3.11.16, so the 3.11.16 this harness reports is provably uv's, not the
# system one. If that ever reads 3.11.2, the reproduction has broken and the run is not evidence.
# them reproduces an ordinary machine; it does NOT pre-resolve anything UACP needs.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git tini procps xz-utils libatomic1 build-essential python3 jq \
    && rm -rf /var/lib/apt/lists/*

# A normal (unprivileged) user's install, not root's.
RUN useradd -m -u 1000 agent
ENV HERMES_HOME=/home/agent/.hermes
ENV PATH=/home/agent/.local/bin:/home/agent/.hermes/bin:$PATH
# Keep the interpreter choice HERMES', not the base image's. The `python3` installed above (for
# node-gyp) is a 3.11 that `uv python find 3.11` would otherwise happily adopt — and it did: the
# first run after adding it reported 3.11.2, Debian's, instead of uv's 3.11.16, silently turning the
# floor reproduction into a test of whatever the base image ships. `only-managed` forces uv to use
# ONLY interpreters it downloaded itself, restoring "let Hermes' installer select the interpreter".
ENV UV_PYTHON_PREFERENCE=only-managed

# Reproducible pin: install.sh @ commit 5fc308a (sha256 c0380bc1...) with `--commit 5fc308a` ==
# Hermes git tag v2026.8.27. Pinned independently so a future install.sh change cannot silently move
# the runtime under the harness.
#
# BUMP THE PIN DELIBERATELY, and re-run. A pin nobody advances turns a green harness into proof about
# an environment no user runs any more — the same shape of stale claim this harness exists to kill.
# NOTE: tools/proving-ground/images/hermes/Dockerfile still pins 2bd1977 (v2026.6.19); that is a cell
# image with its own cadence, so the two now DIVERGE on purpose rather than by neglect.
ARG HERMES_COMMIT=5fc308a70719a83cccdbba4c0e39c23f5a8239d5
ARG HERMES_INSTALL_SHA256=c0380bc1f78d3d662a77663ce20cc17e14cbc4bec35e61ab7a33bac5f3afed2d

USER agent
WORKDIR /home/agent
RUN curl -fsSL "https://raw.githubusercontent.com/NousResearch/hermes-agent/${HERMES_COMMIT}/scripts/install.sh" \
      -o /tmp/install-hermes.sh && \
    echo "${HERMES_INSTALL_SHA256}  /tmp/install-hermes.sh" | sha256sum -c - && \
    bash /tmp/install-hermes.sh --commit "${HERMES_COMMIT}" --skip-setup --skip-browser && \
    rm /tmp/install-hermes.sh

# The repo present only as the SOURCE the symlink binding points at — the same role the local
# marketplace plays for Claude Code. It is never added to sys.path or imported by the harness.
COPY --chown=agent:agent . /uacp
ENV UACP_ROOT=/uacp

COPY --chown=agent:agent acceptance/hermes/run.sh /run.sh
COPY --chown=agent:agent acceptance/hermes/probe.sh /probe.sh
USER root
RUN chmod +x /run.sh /probe.sh
USER agent

WORKDIR /home/agent
ENTRYPOINT ["tini", "--"]
CMD ["/run.sh"]
