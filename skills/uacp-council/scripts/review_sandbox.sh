#!/usr/bin/env bash
# Review sandbox provisioning — uacp-bridge "Review Containment" Tier 2 (ephemeral worktree).
#
# For capability_profile=inspect, the orchestrator MUST run reviewers against a
# disposable copy of the scope, never the live working tree, so a shelled-out
# reviewer's stray writes land in throwaway space (the Guardian PreToolUse hook
# does NOT see a child process's own filesystem I/O — see uacp-bridge/SKILL.md).
#
# This provisions a DETACHED git worktree (on-pattern with docs/lifecycle/worktree-protocol.md):
# disposable, isolated from the live tree, auto-removable.
#
# Usage:
#   review_sandbox.sh provision <session_id> [ref] [evidence_file]  # prints the sandbox path on stdout
#   review_sandbox.sh teardown  <session_id>
#
# On provision, if a fourth arg is given, a run-bound provisioning EVIDENCE record is written there
# as JSON: {"tool","session","ref","worktree","provisioned":true}. This is the artifact the
# council-synthesis validator (validate_council_reviewer_grounding, D-17) requires a reviewer's
# read_only_enforcement claim to resolve to — the read-only claim must ground on the ACTUAL
# provisioning result, not a self-declared boolean. stdout stays the sandbox path only, so callers
# capturing $SANDBOX are unaffected.
#
# Exit codes: 0 ok · 2 usage error · 1 git/provision failure (caller fail-closes to SKIP).
set -euo pipefail

cmd="${1:-}"
session="${2:-}"
ref="${3:-HEAD}"
evidence_file="${4:-}"

if [ -z "$cmd" ] || [ -z "$session" ]; then
  echo "usage: review_sandbox.sh <provision|teardown> <session_id> [ref]" >&2
  exit 2
fi

# Sanitize the session id to a safe path segment (defense against path traversal).
safe="$(printf '%s' "$session" | tr -cd '[:alnum:]_-')"
if [ -z "$safe" ]; then
  echo "review_sandbox: invalid session id (no safe characters)" >&2
  exit 2
fi

root="$(git rev-parse --show-toplevel)"
path="$root/.worktrees/review-$safe"

# Write a run-bound provisioning evidence record (JSON) to $evidence_file, if requested. The
# session id is JSON-escaped defensively (it is already sanitized to $safe for the path, but the
# raw value is echoed into the record). Never fails the provision on an evidence-write hiccup.
write_evidence() {
  [ -n "$evidence_file" ] || return 0
  mkdir -p "$(dirname "$evidence_file")" 2>/dev/null || true
  printf '{"tool":"review_sandbox.sh","session":"%s","ref":"%s","worktree":"%s","provisioned":true}\n' \
    "$safe" "$ref" "$path" > "$evidence_file" 2>/dev/null || true
}

case "$cmd" in
  provision)
    # Idempotent: if the sandbox worktree already exists, reuse it.
    if git -C "$root" worktree list --porcelain | grep -qx "worktree $path"; then
      write_evidence
      echo "$path"
      exit 0
    fi
    # Detached so we never check out / squat a named branch.
    git -C "$root" worktree add --detach --quiet "$path" "$ref" >&2
    write_evidence
    echo "$path"
    ;;
  teardown)
    git -C "$root" worktree remove --force "$path" 2>/dev/null || rm -rf "$path"
    git -C "$root" worktree prune >/dev/null 2>&1 || true
    ;;
  *)
    echo "review_sandbox: unknown command '$cmd'" >&2
    exit 2
    ;;
esac
