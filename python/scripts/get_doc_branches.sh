#!/bin/bash
# Script to dynamically determine which branches to build documentation for
# This makes the workflow work on forks that may not have all release branches
#
# Usage: get_doc_branches.sh <current_branch_name>
#
# Returns: Space-separated list of branches for sphinx-versioned

set -e

CURRENT_BRANCH="$1"

if [ -z "$CURRENT_BRANCH" ]; then
    echo "Error: Current branch name must be provided as first argument" >&2
    exit 1
fi

# Initialize branch list with current branch
BRANCHES="$CURRENT_BRANCH"

# Add master if it exists and isn't already in the list
if git ls-remote --heads origin master >/dev/null 2>&1; then
    if [ "$CURRENT_BRANCH" != "master" ]; then
        BRANCHES="$BRANCHES master"
    fi
fi

# Add all release branches that exist
# Note: We check for remote branches to handle forks properly
for branch in $(git ls-remote --heads origin | grep -E 'refs/heads/release-' | sed 's/.*refs\/heads\///'); do
    # Skip if already in list (shouldn't happen with release branches, but be safe)
    if [[ ! " $BRANCHES " =~ " $branch " ]]; then
        BRANCHES="$BRANCHES $branch"
    fi
done

# Output the branch list
echo "$BRANCHES"