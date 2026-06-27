#!/usr/bin/env bash
# Mirror of the branch-name check in pr-policy.yml — catches violations client-side.
set -euo pipefail

branch=$(git rev-parse --abbrev-ref HEAD)

# Two disjoint alternatives (matches pr-policy.yml exactly):
#   1. dependabot/<ecosystem>/<rest>  — underscores OK
#   2. Standard: lowercase, alphanumeric segments separated by hyphens or slashes
DEPENDABOT='^dependabot/[a-z0-9_-]+/.+'
STANDARD='^[a-z][a-z0-9]*([/-][a-z0-9]+)*$'

if [[ "$branch" =~ $DEPENDABOT ]] || [[ "$branch" =~ $STANDARD ]]; then
  exit 0
fi

echo "pre-push: branch name '$branch' violates convention."
echo "  Format : type/description  or  type-description"
echo "  Examples: feat/add-oracle, fix-timeout, chore/update-deps"
echo "  (Underscores are only allowed in dependabot/ branches.)"
exit 1
