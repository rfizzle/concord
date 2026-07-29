#!/usr/bin/env bash
# Sync every sibling member repo: checkout master, fast-forward pull, and
# prune stale branches (remote-tracking refs via fetch --prune, plus local
# branches whose upstream is gone or that are fully merged into master).
#
# Safety rails:
#   - a repo with uncommitted changes is skipped untouched
#   - never force-deletes the checked-out branch or master
#   - gone-upstream branches are deleted with -D (the PR squash-merge flow
#     means -d can never see the merge); each deletion prints the tip SHA so
#     `git branch <name> <sha>` can resurrect it
#
# Usage: scripts/pull-members.sh [member ...]   (default: all of members.json)
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -gt 0 ]]; then
    members=("$@")
else
    mapfile -t members < <(jq -r '.members[].id' members.json)
fi

failures=()
skipped=()

for m in "${members[@]}"; do
    repo="../$m"
    echo "=== $m ==="
    if [[ ! -d "$repo/.git" ]]; then
        echo "  skip: $repo is not a git checkout"
        skipped+=("$m (missing)")
        continue
    fi

    if [[ -n "$(git -C "$repo" status --porcelain)" ]]; then
        echo "  skip: uncommitted changes — leaving untouched"
        skipped+=("$m (dirty)")
        continue
    fi

    if ! git -C "$repo" checkout --quiet master; then
        echo "  FAIL: could not checkout master"
        failures+=("$m (checkout)")
        continue
    fi

    if ! git -C "$repo" pull --ff-only --prune; then
        echo "  FAIL: pull --ff-only failed (diverged from origin/master?)"
        failures+=("$m (pull)")
        continue
    fi

    # Local branches fully merged into master: safe delete.
    while IFS= read -r br; do
        [[ -z "$br" || "$br" == "master" ]] && continue
        git -C "$repo" branch --quiet -d "$br" \
            && echo "  pruned (merged): $br"
    done < <(git -C "$repo" branch --merged master --format='%(refname:short)')

    # Local branches whose upstream is gone (deleted after PR merge).
    while IFS= read -r br; do
        [[ -z "$br" || "$br" == "master" ]] && continue
        sha=$(git -C "$repo" rev-parse --short "$br")
        git -C "$repo" branch --quiet -D "$br" \
            && echo "  pruned (gone upstream): $br  [was $sha]"
    done < <(git -C "$repo" for-each-ref refs/heads \
                 --format='%(refname:short) %(upstream:track)' \
             | awk '$2 == "[gone]" {print $1}')

    echo "  ok: $(git -C "$repo" log --oneline -1)"
done

echo
echo "=== summary ==="
echo "synced:  $(( ${#members[@]} - ${#failures[@]} - ${#skipped[@]} ))/${#members[@]}"
[[ ${#skipped[@]}  -gt 0 ]] && printf 'skipped: %s\n' "${skipped[*]}"
[[ ${#failures[@]} -gt 0 ]] && { printf 'FAILED:  %s\n' "${failures[*]}"; exit 1; }
exit 0
