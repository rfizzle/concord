#!/usr/bin/env python3
"""Sync Concord-owned regions into a member repo's AGENTS.md.

Reads the canonical region bodies from AGENTS-COMMON.md (the text between each
`<!-- concord:NAME:start -->` / `<!-- concord:NAME:end -->` pair) and replaces
the matching region in the target AGENTS.md, leaving everything outside the
markers — and the marker lines themselves — untouched.

A region is only written if the target already carries BOTH markers, so this is
inert on a repo that hasn't opted in; seeding the markers once is the per-repo
opt-in. Idempotent: re-running with no upstream change rewrites nothing.

    python3 scripts/inject-agents-regions.py <regions-source> <target-agents-md>

Exit status: 0 and prints "changed" if the target was modified, "unchanged"
otherwise; 2 on a malformed region source. Used by propagate.yml and for the
initial local seeding of member repos.
"""

from __future__ import annotations

import re
import sys


def _markers(name: str) -> tuple[str, str]:
    return f"<!-- concord:{name}:start -->", f"<!-- concord:{name}:end -->"


def parse_regions(source: str) -> dict[str, str]:
    """Map region name -> inner body (exclusive of the marker lines)."""
    pattern = re.compile(
        r"<!-- concord:(?P<name>[a-z0-9-]+):start -->\n"
        r"(?P<body>.*?)"
        r"\n<!-- concord:(?P=name):end -->",
        re.DOTALL,
    )
    regions = {m.group("name"): m.group("body") for m in pattern.finditer(source)}
    if not regions:
        print("no concord:* regions found in source", file=sys.stderr)
        raise SystemExit(2)
    return regions


def inject(target: str, regions: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """Return (new_text, names_applied, names_skipped_missing_marker)."""
    applied, skipped = [], []
    out = target
    for name, body in regions.items():
        start, end = _markers(name)
        if start not in out or end not in out:
            skipped.append(name)
            continue
        # Replace whatever sits between the marker lines with the canonical body,
        # preserving the markers and a single blank-free newline boundary.
        block = re.compile(
            re.escape(start) + r"\n.*?\n" + re.escape(end), re.DOTALL
        )
        out = block.sub(f"{start}\n{body}\n{end}", out, count=1)
        applied.append(name)
    return out, applied, skipped


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    source_path, target_path = argv
    with open(source_path, encoding="utf-8") as f:
        regions = parse_regions(f.read())
    with open(target_path, encoding="utf-8") as f:
        original = f.read()

    new_text, applied, skipped = inject(original, regions)
    if skipped:
        print(f"skipped (no marker in target): {', '.join(skipped)}", file=sys.stderr)
    if new_text != original:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print(f"changed: {target_path} (regions: {', '.join(applied)})")
    else:
        print(f"unchanged: {target_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
