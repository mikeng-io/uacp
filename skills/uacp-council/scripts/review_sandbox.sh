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
#   review_sandbox.sh provision <session_id> [ref]   # prints the sandbox path on stdout
#   review_sandbox.sh teardown  <session_id>
#
# Exit codes: 0 ok · 2 usage error · 1 git/provision failure (caller fail-closes to SKIP).
set -euo pipefail

cmd="${1:-}"
session="${2:-}"
ref="${3:-HEAD}"

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

case "$cmd" in
  provision)
    # Idempotent: if the sandbox worktree already exists, reuse it.
    if git -C "$root" worktree list --porcelain | grep -qx "worktree $path"; then
      echo "$path"
      exit 0
    fi
    # Detached so we never check out / squat a named branch.
    git -C "$root" worktree add --detach --quiet "$path" "$ref" >&2
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
