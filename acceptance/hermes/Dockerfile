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
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git tini procps xz-utils jq \
    && rm -rf /var/lib/apt/lists/*

# A normal (unprivileged) user's install, not root's.
RUN useradd -m -u 1000 agent
ENV HERMES_HOME=/home/agent/.hermes
ENV PATH=/home/agent/.local/bin:/home/agent/.hermes/bin:$PATH

# Reproducible pin, reused verbatim from tools/proving-ground/images/hermes/Dockerfile:
# install.sh @ commit 2bd1977 (sha256 dbd9d555...) with `--commit 2bd1977` == Hermes git tag
# v2026.6.19 == `hermes v0.17.0`. Pinned independently so a future install.sh change cannot silently
# move the runtime under the harness.
ARG HERMES_COMMIT=2bd1977d8fad185c9b4be47884f7e87f1add0ce3
ARG HERMES_INSTALL_SHA256=dbd9d555ed4ac67bd1fc71ba6a39b410cf2af0ebcfd8f4889e086af78c9ddcaa

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
