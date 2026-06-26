# UACP E2E acceptance — Increment 0: reproduce a NORMAL USER installing the plugin (design nodes 10/11/13).
#
# The point is to hit exactly what a real Claude Code user hits — so the baseline is ONLY what such a
# user has: Claude Code + uv (both standard developer tools), installed their official way. We do NOT
# WARM any cache or pre-resolve the plugin's deps: if the plugin's first real launch is broken, that
# is a PRODUCT defect this test must EXPOSE, not paper over. The harness installs the plugin the
# published way (`claude plugin marketplace add` + `claude plugin install`) and observes Claude Code's
# OWN report — it never reads the plugin source or launches anything itself.
FROM debian:bookworm-slim

# Enough to fetch + run Claude Code and do a marketplace install.
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# The standard developer baseline a normal user has: uv (the plugin's MCP launcher prereq) + Claude
# Code (the runtime). Installed their official ways. NO cache warming, NO pre-resolved plugin deps.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

# The repo present only as the local marketplace SOURCE the user installs FROM.
COPY . /uacp
COPY acceptance/run.sh /run.sh
RUN chmod +x /run.sh

# Do the user's flow + report Claude Code's own verdict. Exit non-zero if the install doesn't work.
CMD ["/run.sh"]
