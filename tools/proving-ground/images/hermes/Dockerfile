# Proving Ground -- hermes-bare cell image (S1).
#
# A minimal Hermes ACP cell: python:3.12-slim + a PINNED Hermes install + a baked HERMES_HOME
# config template that is rendered from the runtime env contract (OPENAI_BASE_URL / OPENAI_API_KEY
# / UACP_MODEL_ID) by the entrypoint. entrypoint default = `hermes acp`.
#
# Install recipe MINED from OpenAB's Dockerfile.hermes (pinned install.sh commit + sha256), but
# adapted: OpenAB builds its Rust broker as a supervisor and installs Hermes as root under the FHS
# layout; we drop the broker entirely (S0 proved the runner spawns `hermes acp` directly) and
# install Hermes as the unprivileged `agent` user so everything lands under /home/agent with no
# cross-user permission dance. Browser tools and the interactive setup wizard are skipped -- the
# cell only needs the ACP adapter.
#
# Reproducible pin: install.sh @ commit 2bd1977 (sha256 dbd9d555...) with `--commit 2bd1977` ==
# Hermes git tag v2026.6.19 == the host-probed `hermes v0.17.0`. Only build-time network fetches
# occur; at runtime the sole outbound dependency is the model endpoint in OPENAI_BASE_URL.
FROM python:3.12-slim

# Hermes v0.17.0 (tag v2026.6.19). The install.sh commit and the checked-out Hermes commit are the
# same sha here because v2026.6.19's tag points at the install.sh commit; pinned independently so a
# future install.sh change cannot silently move the runtime.
ARG HERMES_COMMIT=2bd1977d8fad185c9b4be47884f7e87f1add0ce3
ARG HERMES_INSTALL_SHA256=dbd9d555ed4ac67bd1fc71ba6a39b410cf2af0ebcfd8f4889e086af78c9ddcaa

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git tini xz-utils procps && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 agent

ENV HERMES_HOME=/home/agent/.hermes
ENV PATH=/home/agent/.local/bin:/home/agent/.hermes/bin:$PATH

# Install Hermes as the agent user (build-time network only), pinned + checksum-verified.
USER agent
WORKDIR /home/agent
RUN curl -fsSL "https://raw.githubusercontent.com/NousResearch/hermes-agent/${HERMES_COMMIT}/scripts/install.sh" \
      -o /tmp/install-hermes.sh && \
    echo "${HERMES_INSTALL_SHA256}  /tmp/install-hermes.sh" | sha256sum -c - && \
    bash /tmp/install-hermes.sh --commit "${HERMES_COMMIT}" --skip-setup --skip-browser && \
    rm /tmp/install-hermes.sh && \
    hermes acp --check

COPY --chown=agent:agent config.yaml.template /opt/proving-ground/config.yaml.template
COPY --chown=agent:agent entrypoint.sh /opt/proving-ground/entrypoint.sh
RUN chmod +x /opt/proving-ground/entrypoint.sh

WORKDIR /workspace
ENTRYPOINT ["tini", "--", "/opt/proving-ground/entrypoint.sh"]
