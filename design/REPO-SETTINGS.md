# Repo Settings Standard — GitHub-side configuration for every member

[`REPO-LAYOUT.md`](../REPO-LAYOUT.md) governs what lives in a member repo's
tree; this document governs the GitHub settings wrapped around it. This
checklist is the enforcement for all of them except the issue labels (§6),
which `propagate.yml` reconciles automatically from
[`labels.json`](../labels.json). Apply it when bootstrapping a repo
([`BOOTSTRAP-CHECKLIST.md`](BOOTSTRAP-CHECKLIST.md) Phase 3 links here) and
audit against it with the script in §8. Every `gh` snippet takes the mod id as
`$MOD` (repo name == mod id).

## 1. General

- [ ] **Description** follows the three-part formula — fixed opener, hook,
      fixed closer:
      `A standalone Minecraft 1.21.1 Fabric mod overhauling <domain>. <One or
      two sentences: the tagline's idea, then the headline features.> Part of
      the Concord collection.`
- [ ] **Website** is `https://<mod>.rfizzle.com`.
- [ ] **Topics**: `minecraft`, `mod`.
- [ ] **Issues** on, **Discussions** off. Wikis and Projects stay at GitHub's
      defaults (on) but are unused — the site and `design/` carry the docs.
- [ ] **Visibility**: private while in development, public at first release.
      Going public is what activates the §7 security features and lets the
      Pages site serve anonymously.

```bash
gh repo edit rfizzle/$MOD --homepage "https://$MOD.rfizzle.com" \
  --add-topic minecraft --add-topic mod \
  --enable-issues --enable-discussions=false
```

## 2. Pull requests & merging — squash-only

- [ ] **Squash merging** is the only enabled method; merge commits and rebase
      merging are off.
- [ ] Squash commit defaults: title from the **PR title** (`PR_TITLE`), body
      from the **commit messages** (`COMMIT_MESSAGES`) — the GitHub UI option
      "Default to pull request title and commit details". PR titles are
      Conventional Commits, so the squash lands on `master` as one
      conventional commit with the branch history in the body.
- [ ] **Automatically delete head branches** on.
- [ ] Auto-merge off; "Always suggest updating pull request branches" off.

```bash
gh repo edit rfizzle/$MOD --enable-squash-merge --enable-merge-commit=false \
  --enable-rebase-merge=false --delete-branch-on-merge \
  --enable-auto-merge=false
gh api -X PATCH repos/rfizzle/$MOD \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=COMMIT_MESSAGES
```

## 3. Branch protection on `master`

One classic branch protection rule on `master` (no rulesets). Its purpose is
to force *everything* — human, Claude workflow, and `concord-sync` PR alike —
through a pull request, without demanding a second account's approval from a
solo maintainer.

- [ ] **Require a pull request before merging**, required approvals **0**.
- [ ] **Require status checks**: strict ("require branches to be up to date"),
      with **no named contexts** — CI gates via the PR checks themselves, and
      an empty required list means a new member is never blocked on a check
      that hasn't run yet.
- [ ] **Do not allow bypassing the above settings** (applies to admins). This
      is why `propagate.yml` proposes changes as `concord-sync` PRs instead of
      pushing.
- [ ] Force pushes and branch deletion blocked.
- [ ] Everything else off: signatures, linear history (squash-only merging
      already yields one), conversation resolution, code-owner review, branch
      lock.

```bash
gh api -X PUT repos/rfizzle/$MOD/branches/master/protection --input - <<'EOF'
{
  "required_status_checks": { "strict": true, "contexts": [] },
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "enforce_admins": true,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

## 4. Actions

- [ ] Actions enabled, **all actions allowed** (the repos run only the
      concord reusable workflows plus their pinned marketplace actions;
      [`workflow-stubs.json`](../workflow-stubs.json) is the drift guard, not
      an allowlist).
- [ ] **Default workflow token: read-only.** Each stub escalates per-job via
      its pinned `permissions:` block — the least-privilege contract
      `make stubs-check` enforces.
- [ ] **"Allow GitHub Actions to create and approve pull requests"** ticked —
      the Claude workflows open and review PRs with the workflow token.
- [ ] **Secrets** (repo-level; no repo variables):
      | Secret | Needed by | When |
      |---|---|---|
      | `CLAUDE_CODE_OAUTH_TOKEN` | `claude-review`, `claude-spec`, `claude-mention`, `mod-release` | bootstrap (Phase 3) |
      | `MODRINTH_TOKEN` | `mod-release`, `mod-listing-sync` | first release |
      | `CURSEFORGE_TOKEN` | `mod-release` | first release |

```bash
gh api -X PUT repos/rfizzle/$MOD/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true
gh secret set CLAUDE_CODE_OAUTH_TOKEN -R rfizzle/$MOD
```

## 5. Pages

- [ ] **Source: GitHub Actions** (`build_type: workflow`) — the `site.yml`
      stub deploys via the reusable `build-site.yml`; nothing serves from a
      branch.
- [ ] **Custom domain** `<mod>.rfizzle.com`.
- [ ] **Enforce HTTPS stays unticked**: the `rfizzle.com` domains are proxied
      through Cloudflare, which terminates TLS in front of Pages, so GitHub
      never provisions its own certificate for the domain.
- [ ] The `github-pages` environment's deployment branch policy allows
      `master` (GitHub manages this when the first deploy runs from
      `master`).

```bash
gh api -X POST repos/rfizzle/$MOD/pages -f build_type=workflow 2>/dev/null \
  || gh api -X PUT repos/rfizzle/$MOD/pages -f build_type=workflow
gh api -X PUT repos/rfizzle/$MOD/pages -f cname="$MOD.rfizzle.com"
```

## 6. Issue labels

[`labels.json`](../labels.json) is the single source of truth for the suite's
issue labels, and `propagate.yml` reconciles it onto every member: missing
labels created, drifted color/description updated in place, and any label not
in the manifest (a repo-local one, dependabot's) left untouched — nothing is
ever deleted. So this section is a mirror of the manifest, not a place to apply
labels by hand; edit `labels.json`, not the repos.

GitHub's nine default labels stay (the manifest pins `bug` to GitHub's own
color and description so a fresh repo is never without it); the suite labels
below join them. The lifecycle four drive the issue flow in
[`AGENTS-COMMON.md`](../AGENTS-COMMON.md) — `needs-spec` fires `claude-spec.yml`,
which swaps it for `ready` or `open-questions`, and `jules` hands off to the
coding agent.

| Label | Color | Purpose |
|---|---|---|
| `needs-spec` | `#1d76db` | Issue needs a spec — triggers `claude-spec.yml` |
| `ready` | `#0e8a16` | Spec complete, no open questions — ready to implement |
| `open-questions` | `#d93f0b` | Spec raised open questions needing a human ruling |
| `jules` | `#5319e7` | Hands the issue to Jules for a draft PR |
| `integration` | `#0052cc` | Cross-mod (Concord) integration / compat work |
| `exploratory` | `#c2e0c6` | Exploratory / not-yet-committed change; needs playtesting |
| `regression` | `#b60205` | Worked in a previous release, now broken |
| `balance` | `#fbca04` | Gameplay balance / tuning adjustment |
| `blocked` | `#e11d21` | Blocked on an upstream fix or another issue |
| `compat` | `#c5def5` | Third-party (non-Concord) mod compatibility |

A fresh repo picks these up on the next `propagate.yml` run; to apply or refresh
them on demand, run the same script the workflow does (needs `GH_TOKEN` with
Issues: write), or `--check` to preview the drift without writing:

```bash
python3 scripts/sync-labels.py rfizzle/$MOD           # from the concord repo root
python3 scripts/sync-labels.py rfizzle/$MOD --check   # report drift, write nothing
```

## 7. Security (public repos)

These activate when the repo goes public at release:

- [ ] **Secret scanning** and **push protection** on (GitHub's public-repo
      defaults — verify they weren't opted out).
- [ ] Dependabot alerts and security updates **off** — the dependency surface
      is the Loom/Fabric toolchain, version-pinned by the mod's Minecraft
      target; bump PRs against a pinned target are noise.

## 8. Audit

Run from anywhere; flags any deviation by eye against the sections above:

```bash
for MOD in meridian mercantile tribulation prosperity respite distillation cultivation instinct; do
  echo "=== $MOD ==="
  gh api repos/rfizzle/$MOD --jq '{visibility, homepage, topics,
    has_discussions, allow_merge_commit, allow_rebase_merge, allow_squash_merge,
    delete_branch_on_merge, squash_merge_commit_title, squash_merge_commit_message,
    security_and_analysis}'
  gh api repos/rfizzle/$MOD/branches/master/protection --jq '{
    strict: .required_status_checks.strict, contexts: .required_status_checks.contexts,
    approvals: .required_pull_request_reviews.required_approving_review_count,
    enforce_admins: .enforce_admins.enabled, force_pushes: .allow_force_pushes.enabled,
    deletions: .allow_deletions.enabled}'
  gh api repos/rfizzle/$MOD/actions/permissions/workflow
  gh api repos/rfizzle/$MOD/actions/secrets --jq '[.secrets[].name]'
  gh api repos/rfizzle/$MOD/pages --jq '{build_type, cname}'
  gh api repos/rfizzle/$MOD/labels --jq '[.[].name] - ["bug","documentation","duplicate","enhancement","good first issue","help wanted","invalid","question","wontfix"]'
done

# The labels row lists each repo's non-default labels; compare against the suite
# set in labels.json (propagate.yml keeps them in sync — a mismatch means the
# workflow has not run there yet, or the repo carries an extra local label).
```

Expected: squash-only merging with `PR_TITLE`/`COMMIT_MESSAGES`, branch
deletion on merge, the §3 protection shape, read-only workflow token with PR
approval allowed, the three secrets (release tokens may lag until first
release), workflow-built Pages on the custom domain, and the suite labels from
[`labels.json`](../labels.json) in the final list.
