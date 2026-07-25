#!/usr/bin/env python3
"""Run the vendored art verifiers across one repo, or across every member.

Both art skills rest on the same rule: the `.glyph`/`.sfx` under `art/` is the
source of truth and the copy under `assets/` is derived from it, so re-touching
an asset means editing the spec and re-rendering. `glyph.py --verify-all` and
`sfx.py --verify-all` enforce that inside a repo — and because they ship with
the skills, every member repo has them.

This script is only the multi-repo driver: it invokes those two, in one repo or
in all of them. Nothing here duplicates the walk, so a member running the
vendored renderer directly gets exactly the same answer concord does.

    python3 scripts/check-art-repeatability.py               # this repo
    python3 scripts/check-art-repeatability.py --root ../mercantile
    python3 scripts/check-art-repeatability.py --root .. --all-members

Exits non-zero when a shipped asset has drifted from its spec.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLYPH = ROOT / ".ai" / "skills" / "mc-textures" / "scripts" / "glyph.py"
SFX = ROOT / ".ai" / "skills" / "mc-audio" / "scripts" / "sfx.py"
VERIFIERS = ((GLYPH, "art/glyphs"), (SFX, "art/audio"))


def check_repo(repo, verbose=False):
    """Run both verifiers in `repo`. Returns (ok, printed_anything)."""
    ok, printed = True, False
    for script, subdir in VERIFIERS:
        if not (repo / subdir).exists():
            continue
        cmd = [sys.executable, str(script), "--verify-all", subdir]
        if verbose:
            cmd.append("--verbose")
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=repo)
        output = (proc.stdout or "") + (proc.stderr or "")
        for line in output.rstrip().splitlines():
            print(f"  {line.strip()}" if line.strip() else "")
        printed = True
        if proc.returncode:
            ok = False
    return ok, printed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="repo to check (default: cwd)")
    ap.add_argument("--all-members", action="store_true",
                    help="treat --root as the directory holding every member "
                         "repo and check each one listed in members.json")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="also list the assets that verified clean")
    args = ap.parse_args(argv)

    roots = [Path(args.root)]
    if args.all_members:
        members = json.loads((ROOT / "members.json").read_text())["members"]
        roots = [Path(args.root) / m["id"] for m in members]

    failed = []
    for repo in roots:
        if not repo.exists():
            print(f"skip: {repo} not found")
            continue
        if not (repo / "art").exists():
            continue
        print(f"{repo}:")
        ok, printed = check_repo(repo, args.verbose)
        if not printed:
            print("  no art specs found")
        if not ok:
            failed.append(repo)

    if failed:
        print(f"\ndrift in: {', '.join(str(r) for r in failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
