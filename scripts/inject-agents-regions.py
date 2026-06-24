#!/usr/bin/env python3
"""Sync a Concord-owned region from a source file into a target file.

Reads the canonical region bodies from a source (the text between each
`concord:NAME:start` / `concord:NAME:end` marker pair) and replaces the matching
region in the target, leaving everything outside the markers — and the marker
lines themselves — untouched.

Markers may be written in either comment style, so one script serves both
Markdown (AGENTS.md) and hash-comment files (.gitignore, YAML):

    <!-- concord:NAME:start -->   |   # concord:NAME:start
    ...                           |   ...
    <!-- concord:NAME:end -->     |   # concord:NAME:end

A region is only written if the target already carries BOTH markers, so this is
inert on a repo that hasn't opted in; seeding the markers once is the per-repo
opt-in. Idempotent: re-running with no upstream change rewrites nothing.

    python3 scripts/inject-agents-regions.py <regions-source> <target-file>

Exit status: 0 and prints "changed" if the target was modified, "unchanged"
otherwise; 2 on a malformed region source. Used by propagate.yml and for the
initial local seeding of member repos.
"""

from __future__ import annotations

import re
import sys

# A start/end marker in either comment style. The `<!--`/`-->` wrappers are
# optional so the same pattern matches both Markdown and hash-comment files.
_OPEN = r"(?:<!--[ \t]*|#[ \t]*)"
_CLOSE = r"(?:[ \t]*-->)?"


def _start(name: str) -> str:
    return _OPEN + r"concord:" + name + r":start" + _CLOSE


def _end(name: str) -> str:
    return _OPEN + r"concord:" + name + r":end" + _CLOSE


def parse_regions(source: str) -> dict[str, str]:
    """Map region name -> inner body (exclusive of the marker lines)."""
    pattern = re.compile(
        _OPEN + r"concord:(?P<name>[a-z0-9-]+):start" + _CLOSE + r"\n"
        r"(?P<body>.*?)"
        r"\n" + _OPEN + r"concord:(?P=name):end" + _CLOSE,
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
        # Match the marker pair in the target and capture the actual marker lines
        # (whatever comment style they use) so they are preserved verbatim.
        block = re.compile(
            r"(?P<start>" + _start(re.escape(name)) + r")\n"
            r".*?\n"
            r"(?P<end>" + _end(re.escape(name)) + r")",
            re.DOTALL,
        )
        m = block.search(out)
        if m is None:
            skipped.append(name)
            continue
        out = out[: m.start()] + f"{m.group('start')}\n{body}\n{m.group('end')}" + out[m.end() :]
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
