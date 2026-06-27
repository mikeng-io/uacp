#!/usr/bin/env bash
# Mirror of the branch-name check in pr-policy.yml — catches violations client-side.
set -euo pipefail

branch=$(git rev-parse --abbrev-ref HEAD)

# Two disjoint alternatives (matches pr-policy.yml exactly):
#   1. dependabot/<ecosystem>/<rest>  — underscores OK
#   2. Typed: an approved TYPE prefix, then hyphen/slash-separated alphanumeric
#      segments. Types mirror the PR-title / type-label taxonomy.
DEPENDABOT='^dependabot/[a-z0-9_-]+/.+'
TYPED='^(feat|fix|chore|docs|design|test|refactor|verify|ci)[/-][a-z0-9]+([/-][a-z0-9]+)*$'

if [[ "$branch" =~ $DEPENDABOT ]] || [[ "$branch" =~ $TYPED ]]; then
  exit 0
fi

echo "pre-push: branch name '$branch' violates convention."
echo "  Format  : <type>/description  or  <type>-description"
echo "  Types   : feat, fix, chore, docs, design, test, refactor, verify, ci"
echo "  Examples: feat/add-oracle, fix-timeout, ci/release-strategy"
echo "  (Underscores are only allowed in dependabot/ branches.)"
exit 1
