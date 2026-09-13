# UACP E2E acceptance — `runner:hermes-onboarding`: agent-native onboarding conformance.
#
# The execute-profile sibling of ../hermes/Dockerfile (which is load-conformance-only,
# network_mode: none, no model). Same discipline — reproduce a real install, no warming, no
# shortcuts, assert on the subject's own report — pointed at a different target (trustless's
# public agent API) and with the two things that harness deliberately withholds turned ON: a real
# model and real network, because driving the actual flow is the point here.
#
# WHY debian:bookworm-slim, NOT FROM python
# ------------------------------------------
# Hermes' own install.sh bootstraps `uv`, and `uv` provisions the interpreter (3.11 today). Letting
# Hermes choose keeps this a reproduction of what a real install gets, not an environment we chose
# for convenience. Same rationale as the sibling harness.
#
# NO WARMING, NO SHORTCUTS: no pre-resolved deps, no source mount, no cache priming, no pre-fetched
# llms.txt, no pre-seeded identity/memory. If the documented flow is broken, this exposes it.
FROM debian:bookworm-slim

# Harness tooling (curl, jq, git, tini) + a GENERIC developer sandbox: python3/pip/node/npm,
# openssl, and enough of a build toolchain for an ordinary pip wheel (e.g. eth-account's coincurve)
# to install. This is what any capable coding-agent host would carry — nothing here is
# trustless-specific, and the agent under test is told nothing about cryptography or this API
# beyond what llms.txt itself says.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git tini procps jq xz-utils coreutils \
      python3 python3-pip python3-venv python3-dev \
      nodejs npm openssl build-essential libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 agent
ENV HERMES_HOME=/home/agent/.hermes
ENV PATH=/home/agent/.local/bin:/home/agent/.hermes/bin:$PATH

# Reproducible pin: install.sh @ commit 939e45c91d751fadd94dcd1b873ac3cb44846213
# (tag v2026.9.11 == Hermes Agent v0.21.2) — the latest public release as of this harness's
# creation (2026-09-13). Unlike the sibling harness's pin (frozen deliberately to reproduce one
# historical defect), THIS pin should be renewed periodically so the harness tracks what a new
# adopter actually gets. Re-pinning is a deliberate, recorded renewal — never done silently to make
# a run pass.
ARG HERMES_COMMIT=939e45c91d751fadd94dcd1b873ac3cb44846213
ARG HERMES_INSTALL_SHA256=5854b15670b51a8daae8f59ddfa917062de9f74be261eb73b4b8d719710f8968
USER agent
WORKDIR /home/agent
RUN curl -fsSL "https://raw.githubusercontent.com/NousResearch/hermes-agent/${HERMES_COMMIT}/scripts/install.sh" \
      -o /tmp/install-hermes.sh && \
    echo "${HERMES_INSTALL_SHA256}  /tmp/install-hermes.sh" | sha256sum -c - && \
    bash /tmp/install-hermes.sh --commit "${HERMES_COMMIT}" --skip-setup --skip-browser && \
    rm /tmp/install-hermes.sh

# Hermes eagerly imports every provider adapter at startup (not just the one configured), and
# importing agent/bedrock_adapter.py triggers its own `lazy_deps` mechanism to pip-install boto3
# on the spot — unconditionally, regardless of which provider this run actually uses. That is
# generic Hermes startup overhead, not part of the trustless-specific behavior under test, so (same
# rationale as the Playwright/TUI/Computer-Use installs above) it is paid once here at build time
# instead of on every ephemeral run. Pinned to the version observed triggering it; lazy_deps checks
# for an existing install before acting, so this makes the runtime path a no-op, not a skip.
RUN VIRTUAL_ENV=/home/agent/.hermes/hermes-agent/venv \
      /home/agent/.hermes/bin/uv pip install --compile-bytecode boto3==1.42.89

# A generic crypto-capable sandbox: llms.txt requires the agent to produce its own EOA wallet and
# EIP-712 signature, and the obvious Python/Node libraries for that (eth-account -> coincurve,
# ethers) routinely have to compile libsecp256k1 from source on a slim base image — minutes of CPU,
# not network-bound, and unrelated to trustless's API (same "pay Hermes' own generic overhead once
# at build time" rationale as the boto3 fix above, not a trustless-specific shortcut: it is exactly
# the kind of library any capable coding agent's sandbox would already carry).
USER root
RUN pip3 install --break-system-packages --no-cache-dir eth-account web3 \
    && npm install -g ethers
USER agent

COPY --chown=agent:agent acceptance/hermes-onboarding/config.yaml /home/agent/.hermes/config.yaml
COPY --chown=agent:agent acceptance/hermes-onboarding/prompt.md /home/agent/prompt.md
COPY --chown=agent:agent acceptance/hermes-onboarding/run.sh /run.sh
COPY --chown=agent:agent acceptance/hermes-onboarding/verify.py /verify.py
USER root
RUN chmod +x /run.sh
USER agent
WORKDIR /home/agent
ENTRYPOINT ["tini", "--"]
CMD ["/run.sh"]
