#!/usr/bin/env python3
"""Check that every shipped texture and sound still matches the spec it came from.

Both art skills rest on the same rule: the `.glyph`/`.sfx` under `art/` is the
source of truth and the copy under `assets/` is derived from it, so re-touching
an asset means editing the spec and re-rendering. Nothing enforced that — a
hand-patched PNG or a stale `.ogg` looked exactly like a faithful one.

This walks a repo's `art/glyphs/*.glyph` and `art/audio/*.sfx`, re-renders each
spec that declares where it ships, and compares. A spec with no `ships:` line is
reported as unlinked rather than checked: it has no declared deliverable, so
there is nothing to hold it to.

    python3 scripts/check-art-repeatability.py               # this repo
    python3 scripts/check-art-repeatability.py --root ../mercantile
    python3 scripts/check-art-repeatability.py --root .. --all-members

Exits non-zero when a shipped asset has drifted from its spec.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLYPH = ROOT / ".ai" / "skills" / "mc-textures" / "scripts" / "glyph.py"
SFX = ROOT / ".ai" / "skills" / "mc-audio" / "scripts" / "sfx.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def glyph_ships(path):
    """The `ships:` targets a .glyph declares, in order (empty when it has none)."""
    out = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("ships:"):
            parts = stripped.split(":", 1)[1].split()
            if parts:
                out.append(parts[0])
        elif stripped.lower() in ("legend:", "frame:", "grid:"):
            break  # past the header — later 'ships:' text is grid content
    return out


def sfx_ships(path):
    try:
        shipped = json.loads(path.read_text()).get("ships")
    except (json.JSONDecodeError, OSError):
        return []
    return [shipped] if shipped else []


def verify(script, spec_path, root):
    """Run one renderer's --verify, letting the spec name its own targets."""
    proc = subprocess.run(
        [sys.executable, str(script), str(spec_path), "--verify"],
        capture_output=True, text=True, cwd=root)
    return proc.returncode == 0, (proc.stderr or proc.stdout).strip()


def check_repo(root, verbose=False):
    """Returns (checked, drifted, unlinked) counts, printing as it goes."""
    root = Path(root)
    checked = drifted = 0
    unlinked = []
    jobs = [(GLYPH, sorted((root / "art" / "glyphs").glob("*.glyph")), glyph_ships),
            (SFX, sorted((root / "art" / "audio").glob("*.sfx")), sfx_ships)]
    for script, specs, ships_of in jobs:
        for spec_path in specs:
            declared = ships_of(spec_path)
            rel = spec_path.relative_to(root)
            if not declared:
                unlinked.append(rel)
                continue
            checked += 1
            ok, detail = verify(script, spec_path, root)
            targets = ", ".join(declared)
            if ok:
                if verbose:
                    print(f"  ok      {rel} -> {targets}")
            else:
                drifted += 1
                print(f"  DRIFT   {rel} -> {targets}")
                for line in detail.splitlines():
                    print(f"          {line}")
    for rel in unlinked:
        print(f"  unlinked {rel} — no 'ships:' target, so nothing verifies it")
    return checked, drifted, len(unlinked)


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

    total_checked = total_drifted = total_unlinked = 0
    for repo in roots:
        if not repo.exists():
            print(f"skip: {repo} not found")
            continue
        if not (repo / "art").exists():
            continue
        print(f"{repo}:")
        checked, drifted, unlinked = check_repo(repo, args.verbose)
        if not checked and not unlinked:
            print("  no specs found")
        total_checked += checked
        total_drifted += drifted
        total_unlinked += unlinked

    print(f"\n{total_checked} verified, {total_drifted} drifted, "
          f"{total_unlinked} unlinked")
    return 1 if total_drifted else 0


if __name__ == "__main__":
    raise SystemExit(main())
