#!/usr/bin/env bash
# Propagate concord-owned files into one member repo via a pull request.
#
# Branch-protected members reject direct commits to their default branch, so we
# stage all concord-owned changes on a `concord-sync` branch and open (or update)
# a single PR. Idempotent: the branch is reset to the default-branch head each
# run and the desired files re-applied, so re-running with no upstream change
# produces no PR (and an open PR just gets refreshed).
#
# Concord-owned payloads synced here:
#   - everything under propagate/  (e.g. .github/ISSUE_TEMPLATE/*.yml)
#   - AGENTS.md and .gitignore, but only their concord:* regions, and only if the
#     member already carries the markers (unseeded repos are left untouched).
#   - .ai/skills/** and .ai/commands/** — the vendored skills and slash commands,
#     wholly concord-owned. Mirrors `make sync`'s `rsync -a --delete`: the
#     git-tracked concord tree is the source of truth, and member files under
#     those prefixes that concord no longer ships are removed. The
#     .ai/skills/.concord-rev provenance file records the concord commit the
#     branch was staged from, and bumps only when skill/command content moves.
#
# Usage:  scripts/open-sync-pr.sh <owner/repo>
# Env:    GH_TOKEN with Contents: write + Pull requests: write on the member.
# Run from the concord repo root. GITHUB_SHA labels the commits and stamps
# .concord-rev (falls back to the local HEAD sha outside Actions).
set -euo pipefail

REPO="$1"
BRANCH="concord-sync"
SRC_SHA="${GITHUB_SHA:-$(git rev-parse HEAD 2>/dev/null || echo local)}"
SHORT="${SRC_SHA:0:7}"

DEFAULT=$(gh api "repos/$REPO" -q .default_branch)
HEAD_SHA=$(gh api "repos/$REPO/git/ref/heads/$DEFAULT" -q .object.sha)

work=$(mktemp -d)
declare -A DESIRED   # dest path in member repo -> local file holding the content

# 1) propagate/* — verbatim concord-owned files, mapped to the same relative path
while IFS= read -r src; do
  DESIRED["${src#propagate/}"]="$src"
done < <(find propagate -type f | sort)

# 2) .ai/skills/** and .ai/commands/** — vendored skills and slash commands, at
# the same relative path. Enumerate the git-tracked set (never the working tree)
# so build caches like __pycache__ are excluded; the working-tree file is the
# content source, matching what `make sync` rsyncs. The .concord-rev provenance
# file is staged separately below, only when the vendored content actually moves.
while IFS= read -r src; do
  [ -n "$src" ] && DESIRED["$src"]="$src"
done < <(git ls-files .ai/skills .ai/commands | sort)

# 3) AGENTS.md regions — fetch the member's file, rewrite only the marked regions.
# Use the exit status (not the body) to detect existence: a 404 still prints its
# JSON to stdout, so guard on a real base64 file response, and only stage the
# result if inject succeeds — never let a decode/parse failure ship garbage.
if agents=$(gh api "repos/$REPO/contents/AGENTS.md?ref=$DEFAULT" 2>/dev/null) \
   && [ "$(printf '%s' "$agents" | jq -r '.encoding // empty')" = "base64" ]; then
  printf '%s' "$agents" | jq -r '.content' | base64 -d > "$work/AGENTS.md"
  if python3 scripts/inject-agents-regions.py AGENTS-COMMON.md "$work/AGENTS.md"; then
    DESIRED["AGENTS.md"]="$work/AGENTS.md"
  else
    echo "  warn: skipping AGENTS.md for $REPO (inject failed)" >&2
  fi
fi

# 4) .gitignore region — same treatment as AGENTS.md (markers in hash-comment form).
if gitignore=$(gh api "repos/$REPO/contents/.gitignore?ref=$DEFAULT" 2>/dev/null) \
   && [ "$(printf '%s' "$gitignore" | jq -r '.encoding // empty')" = "base64" ]; then
  printf '%s' "$gitignore" | jq -r '.content' | base64 -d > "$work/.gitignore"
  if python3 scripts/inject-agents-regions.py gitignore-common "$work/.gitignore"; then
    DESIRED[".gitignore"]="$work/.gitignore"
  else
    echo "  warn: skipping .gitignore for $REPO (inject failed)" >&2
  fi
fi

# Which desired files actually differ from the default branch?
changed=()
declare -A BASE_SHA
for dest in "${!DESIRED[@]}"; do
  local_b64=$(base64 -w0 "${DESIRED[$dest]}")
  remote=$(gh api "repos/$REPO/contents/$dest?ref=$DEFAULT" 2>/dev/null || true)
  remote_b64=$(printf '%s' "$remote" | jq -r '.content // empty' | tr -d '\n')
  BASE_SHA["$dest"]=$(printf '%s' "$remote" | jq -r '.sha // empty')
  [ "$local_b64" != "$remote_b64" ] && changed+=("$dest")
done

# --delete semantics for the vendored trees: any member file under .ai/skills/ or
# .ai/commands/ that concord no longer ships must be removed. Enumerate the
# member's blobs under those prefixes (from the default-branch tree) and mark the
# ones absent from DESIRED for deletion. The .concord-rev provenance file is
# concord-generated (concord itself does not carry it), so it is never a deletion
# candidate.
deleted=()
declare -A DEL_SHA
TREE_SHA=$(gh api "repos/$REPO/git/commits/$HEAD_SHA" -q .tree.sha)
while IFS=$'\t' read -r path sha; do
  case "$path" in
    .ai/skills/.concord-rev) : ;;
    .ai/skills/*|.ai/commands/*)
      [ -z "${DESIRED[$path]+x}" ] && { deleted+=("$path"); DEL_SHA["$path"]="$sha"; } ;;
  esac
done < <(gh api "repos/$REPO/git/trees/$TREE_SHA?recursive=1" \
           -q '.tree[] | select(.type=="blob") | "\(.path)\t\(.sha)"')

# Did any vendored skill/command content move (added, updated, or removed)? The
# .concord-rev provenance stamp bumps only when it did — an AGENTS.md-only sync
# leaves the vendored tree, and its recorded revision, untouched.
skills_touched=0
for p in ${changed[@]+"${changed[@]}"} ${deleted[@]+"${deleted[@]}"}; do
  case "$p" in .ai/skills/*|.ai/commands/*) skills_touched=1 ;; esac
done

if [ ${#changed[@]} -eq 0 ] && [ ${#deleted[@]} -eq 0 ]; then
  echo "$REPO: up to date — no PR needed"
  exit 0
fi

# Stamp .ai/skills/.concord-rev with the concord commit the branch is staged from,
# but only when the vendored content moved (otherwise the file, and the PR, would
# churn on every unrelated concord change).
if [ "$skills_touched" -eq 1 ]; then
  rev_dest=".ai/skills/.concord-rev"
  printf '%s\n' "$SRC_SHA" > "$work/.concord-rev"
  local_b64=$(base64 -w0 "$work/.concord-rev")
  remote=$(gh api "repos/$REPO/contents/$rev_dest?ref=$DEFAULT" 2>/dev/null || true)
  remote_b64=$(printf '%s' "$remote" | jq -r '.content // empty' | tr -d '\n')
  if [ "$local_b64" != "$remote_b64" ]; then
    DESIRED["$rev_dest"]="$work/.concord-rev"
    BASE_SHA["$rev_dest"]=$(printf '%s' "$remote" | jq -r '.sha // empty')
    changed+=("$rev_dest")
  fi
fi

echo "$REPO: ${#changed[@]} to write, ${#deleted[@]} to remove: ${changed[*]-} ${deleted[*]-}"

# Reset the sync branch to the current default head (create if missing), so each
# run starts clean and the PR diff is exactly concord's desired changes.
if gh api "repos/$REPO/git/ref/heads/$BRANCH" >/dev/null 2>&1; then
  gh api -X PATCH "repos/$REPO/git/refs/heads/$BRANCH" -f sha="$HEAD_SHA" -F force=true >/dev/null
else
  gh api -X POST "repos/$REPO/git/refs" -f ref="refs/heads/$BRANCH" -f sha="$HEAD_SHA" >/dev/null
fi

# Apply each changed file onto the branch. After the reset, a file's sha on the
# branch equals its sha on default, so BASE_SHA is the right precondition; new
# files carry no sha.
for dest in "${changed[@]}"; do
  content_b64=$(base64 -w0 "${DESIRED[$dest]}")
  file_sha="${BASE_SHA[$dest]}"
  gh api -X PUT "repos/$REPO/contents/$dest" \
    -f message="chore: sync $dest from concord@$SHORT" \
    -f content="$content_b64" \
    -f branch="$BRANCH" \
    ${file_sha:+-f sha="$file_sha"} >/dev/null
  echo "  staged: $dest"
done

# Remove member files concord dropped. After the reset the branch blob sha equals
# the default-branch sha captured above, so DEL_SHA is the right precondition.
for dest in ${deleted[@]+"${deleted[@]}"}; do
  gh api -X DELETE "repos/$REPO/contents/$dest" \
    -f message="chore: sync (remove $dest) from concord@$SHORT" \
    -f sha="${DEL_SHA[$dest]}" \
    -f branch="$BRANCH" >/dev/null
  echo "  removed: $dest"
done

# Open the PR if one isn't already open for this branch.
existing=$(gh pr list -R "$REPO" --head "$BRANCH" --state open --json number -q '.[0].number' 2>/dev/null || true)
if [ -z "$existing" ]; then
  gh pr create -R "$REPO" --base "$DEFAULT" --head "$BRANCH" \
    --title "chore: sync concord-owned files" \
    --body "Automated sync from concord@$SHORT (issue templates, AGENTS.md + .gitignore shared regions, vendored .ai/skills + .ai/commands). Generated by propagate.yml — merge to adopt; the branch refreshes on each concord change."
  echo "$REPO: opened PR"
else
  echo "$REPO: refreshed existing PR #$existing"
fi
