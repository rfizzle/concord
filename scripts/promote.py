#!/usr/bin/env python3
"""Fast-forward the hub's `stable` branch to a master commit, after gating checks.

Members call the hub's reusable workflows `@stable`; canary members (the
`canary` map in workflow-stubs.json) call `@master`. A hub change therefore
reaches the canary on push and reaches every other member only through this
script. `stable` only ever fast-forwards, and only this script moves it.

    python3 scripts/promote.py              # promote origin/master
    python3 scripts/promote.py SHA          # promote a specific commit
    python3 scripts/promote.py --dry-run    # run every gate, push nothing

Each step prints one line and the run stops at the first failure (exit 1):

  1. resolve the target; `origin/stable` must exist and be an ancestor of it
  2. list the commits being promoted
  3. the hub's own check runs on the target are green (none is also fine: hub
     checks are path-filtered)
  4. every hub unit test module (scripts/test_*.py) passes
  5. for each canary member: no open `concord-sync` PR (the hub change has not
     landed there yet), then its CI, dispatched on master, finishes green
  6. push the target to refs/heads/stable (skipped with --dry-run)

Step 5 dispatches the canary's CI, so every member's ci.yml stub must declare
`workflow_dispatch:`.

Needs `git` with push rights on origin and an authenticated `gh`. Run from the
hub repo root.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import time

HUB = "rfizzle/concord"
OWNER = "rfizzle"
SYNC_BRANCH = "concord-sync"
CI_WORKFLOW = "ci.yml"
GOOD_CONCLUSIONS = {"success", "skipped", "neutral"}
CI_TIMEOUT = 45 * 60  # seconds to wait for a canary's CI run
POLL_INTERVAL = 20  # seconds between run-list polls
APPEAR_TIMEOUT = 3 * 60  # seconds for a dispatched run to show up

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Fail(Exception):
    """A gate failed; the message is the one-line reason."""


# --- subprocess helpers (the seam the tests replace) -----------------------


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def git(*args: str, check: bool = True) -> str:
    """stdout of `git <args>`; with check=False returns "" on failure."""
    proc = _run(["git", *args])
    if proc.returncode != 0:
        if check:
            raise Fail(f"git {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
        return ""
    return proc.stdout.strip()


def git_ok(*args: str) -> bool:
    """Whether `git <args>` exits 0 (for yes/no queries like is-ancestor)."""
    return _run(["git", *args]).returncode == 0


def gh(*args: str) -> str:
    proc = _run(["gh", *args])
    if proc.returncode != 0:
        raise Fail(f"gh {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def run_unit_tests(modules: list[str]) -> list[str]:
    """Run each hub test module; return the names of the ones that failed."""
    failed = []
    for mod in modules:
        if _run([sys.executable, "-m", "unittest", mod]).returncode != 0:
            failed.append(mod)
    return failed


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def monotonic() -> float:
    return time.monotonic()


def sleep(seconds: float) -> None:
    time.sleep(seconds)


# --- output ----------------------------------------------------------------


def ok(msg: str) -> None:
    print(f"✓ {msg}")


def info(msg: str) -> None:
    print(f"  {msg}")


# --- gates -----------------------------------------------------------------


def canary_members() -> list[str]:
    data = json.loads((ROOT / "workflow-stubs.json").read_text(encoding="utf-8"))
    return sorted(data.get("canary", {}))


def test_modules() -> list[str]:
    return [f"scripts.{p.stem}" for p in sorted((ROOT / "scripts").glob("test_*.py"))]


def resolve_target(sha: str | None) -> tuple[str, str]:
    """(target sha, stable sha). Fails unless the target fast-forwards stable."""
    git("fetch", "origin")
    stable = git("rev-parse", "--verify", "--quiet", "origin/stable^{commit}", check=False)
    if not stable:
        raise Fail(
            "origin/stable does not exist; create it once with "
            "`git push origin <sha>:refs/heads/stable`"
        )
    spec = sha or "origin/master"
    target = git("rev-parse", "--verify", "--quiet", f"{spec}^{{commit}}", check=False)
    if not target:
        raise Fail(f"cannot resolve {spec} to a commit")
    return target, stable


def check_hub_runs(sha: str) -> int:
    """Fail on any hub check run that is unfinished or not green; return the count."""
    out = gh(
        "api", f"repos/{HUB}/commits/{sha}/check-runs?per_page=100", "--paginate",
        "--jq", ".check_runs[] | {name, status, conclusion}",
    )
    runs = [json.loads(line) for line in out.splitlines() if line.strip()]
    for run in runs:
        if run["status"] != "completed":
            raise Fail(f"hub check '{run['name']}' is {run['status']}")
        if run["conclusion"] not in GOOD_CONCLUSIONS:
            raise Fail(f"hub check '{run['name']}' concluded {run['conclusion']}")
    return len(runs)


def check_no_sync_pr(member: str) -> None:
    out = gh(
        "pr", "list", "-R", f"{OWNER}/{member}", "--state", "open",
        "--head", SYNC_BRANCH, "--json", "url,headRefName",
    )
    for pr in json.loads(out or "[]"):
        if pr.get("headRefName") == SYNC_BRANCH:
            raise Fail(
                f"{member} has an open {SYNC_BRANCH} PR, so the hub change has not "
                f"landed there yet: {pr['url']}"
            )


def _parse_time(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


def _list_runs(member: str) -> list[dict]:
    out = gh(
        "run", "list", "-R", f"{OWNER}/{member}", "--workflow", CI_WORKFLOW,
        "--event", "workflow_dispatch", "--branch", "master",
        "--json", "databaseId,createdAt,status,conclusion,url",
    )
    return json.loads(out or "[]")


def run_canary_ci(member: str) -> str:
    """Dispatch the member's CI on master and wait for it; return the run URL."""
    dispatched = now()
    gh("workflow", "run", CI_WORKFLOW, "-R", f"{OWNER}/{member}", "--ref", "master")
    started = monotonic()
    run = None
    while run is None:
        fresh = [r for r in _list_runs(member) if _parse_time(r["createdAt"]) >= dispatched]
        if fresh:
            run = max(fresh, key=lambda r: r["createdAt"])
            break
        if monotonic() - started > APPEAR_TIMEOUT:
            raise Fail(f"{member} CI did not start after dispatch (does ci.yml declare workflow_dispatch?)")
        sleep(POLL_INTERVAL)
    info(f"{member} CI: {run['url']}")
    while run["status"] != "completed":
        if monotonic() - started > CI_TIMEOUT:
            raise Fail(f"{member} CI timed out after {CI_TIMEOUT // 60} min: {run['url']}")
        sleep(POLL_INTERVAL)
        run = next((r for r in _list_runs(member) if r["databaseId"] == run["databaseId"]), run)
    if run["conclusion"] != "success":
        raise Fail(f"{member} CI concluded {run['conclusion']}: {run['url']}")
    return run["url"]


def promote(sha: str | None, dry_run: bool) -> None:
    target, stable = resolve_target(sha)
    short = target[:10]
    if target == stable:
        print(f"stable is already at {short}")
        return
    if not git_ok("merge-base", "--is-ancestor", stable, target):
        raise Fail(f"{short} is not a descendant of origin/stable ({stable[:10]}); stable only fast-forwards")
    ok(f"{short} fast-forwards stable ({stable[:10]})")

    log = git("log", "--oneline", f"{stable}..{target}")
    ok(f"promoting {len(log.splitlines())} commit(s)")
    for line in log.splitlines():
        info(line)

    runs = check_hub_runs(target)
    ok(f"hub checks green at {short} ({runs} check run(s))")

    modules = test_modules()
    failed = run_unit_tests(modules)
    if failed:
        raise Fail(f"hub unit tests failed: {', '.join(failed)}")
    ok(f"hub unit tests pass ({len(modules)} module(s))")

    for member in canary_members():
        check_no_sync_pr(member)
        ok(f"{member} has no open {SYNC_BRANCH} PR")
        url = run_canary_ci(member)
        ok(f"{member} CI green on master: {url}")

    if dry_run:
        ok(f"dry run: would push {short} to stable")
        return
    git("push", "origin", f"{target}:refs/heads/stable")
    ok(f"stable advanced {stable[:10]} -> {short}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sha", nargs="?", help="commit to promote (default: origin/master)")
    parser.add_argument("--dry-run", action="store_true", help="run every gate but do not push")
    args = parser.parse_args(argv)
    try:
        promote(args.sha, args.dry_run)
    except Fail as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
