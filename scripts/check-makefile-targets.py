#!/usr/bin/env python3
"""Check each member repo's Makefile against the canonical target contract.

A member's Makefile is the same file across the suite with a different jar name.
That uniformity is what lets any agent or human drop into any member repo and
know that `make coverage` means the merged report and `make release` only tags —
but nothing enforced it, so targets went missing where the thing they drive was
fully wired and description strings drifted apart.

What counts as drift, per member:

  - a `universal` target is missing, or its recipe/prerequisites differ from
    makefile-targets.json (after substituting the member id for {modid})
  - a `conditional` target is missing while its `requiredWhen` condition holds
    (e.g. no `coverage` target in a repo whose build.gradle wires
    jacocoMergedReport)
  - the `help` menu describes a target with wording other than the manifest's,
    lists a target the Makefile does not define, omits one it does, or orders
    them against helpOrder
  - a defined target is absent from `.PHONY`, where a same-named file would
    silently shadow it

Everything else is a note: a conditional target absent with its condition not
holding, a target this contract says nothing about, or a member not checked out.
The contract is a floor, not a ceiling — a member is free to add targets.

`help` is deliberately not compared byte-for-byte. It is the one recipe that
legitimately varies, because it lists only the targets that member has; it is
checked as an ordered projection of the manifest's descriptions instead.

Member ids come from members.json; each member repo is read from <root>/<id>/.
Locally that is the sibling checkout (../<member>, the default); in CI a bash
step mirrors each member's Makefile into a temp tree and points --root at it.

    python3 scripts/check-makefile-targets.py            # check ../<member> siblings
    python3 scripts/check-makefile-targets.py --root DIR # check <DIR>/<member>/...

Exit status: 0 when no checked member drifts (notes still pass); 1 on any drift;
2 on a missing/malformed members.json or makefile-targets.json.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

MODID_TOKEN = "{modid}"
TARGET_RE = re.compile(r"^([a-zA-Z][\w-]*)\s*:(?!=)(.*)$")
HELP_RE = re.compile(r'^\t@echo "  ([\w-]+)\s+(.*)"$')
PHONY_RE = re.compile(r"^\.PHONY\s*:(.*)$")


def _load_json(path: pathlib.Path, what: str) -> dict:
    """Load a repo-controlled JSON file, failing with a clean message + exit 2
    (never a raw traceback) on a missing or malformed file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: {what} not found at {path}", file=sys.stderr)
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        print(f"error: {what} is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)


def member_ids(path: pathlib.Path) -> list[str]:
    data = _load_json(path, "members.json")
    return [m["id"] for m in data.get("members", [])]


def load_contract(path: pathlib.Path) -> dict:
    data = _load_json(path, "makefile-targets.json")
    for key in ("universal", "conditional", "helpOrder"):
        if key not in data:
            print(f"error: makefile-targets.json has no '{key}'", file=sys.stderr)
            raise SystemExit(2)
    return data


def parse_makefile(text: str) -> tuple[dict, list[tuple[str, str]], list[str]]:
    """(targets, help_lines, phony) from Makefile source.

    A target's recipe is the run of tab-prefixed lines directly beneath it;
    the first non-tab line ends it, so comments and blank lines between targets
    belong to neither.
    """
    lines = text.splitlines()
    targets: dict[str, dict] = {}
    help_lines: list[tuple[str, str]] = []
    phony: list[str] = []

    for i, line in enumerate(lines):
        described = HELP_RE.match(line)
        if described:
            help_lines.append((described.group(1), described.group(2)))

        declared = PHONY_RE.match(line)
        if declared:
            phony.extend(declared.group(1).split())

        if line.startswith("\t"):
            continue
        matched = TARGET_RE.match(line)
        if not matched:
            continue
        recipe = []
        for following in lines[i + 1:]:
            if not following.startswith("\t"):
                break
            recipe.append(following)
        targets[matched.group(1)] = {
            "prerequisites": matched.group(2).strip(),
            "recipe": recipe,
        }

    return targets, help_lines, phony


def _expected(spec: dict, mod_id: str) -> tuple[str, list[str]]:
    recipe = [line.replace(MODID_TOKEN, mod_id) for line in spec["recipe"]]
    return spec.get("prerequisites", "").replace(MODID_TOKEN, mod_id), recipe


def _condition_holds(member_dir: pathlib.Path, condition: dict) -> bool:
    """True when the member wires the thing a conditional target drives."""
    probe = member_dir / condition["file"]
    try:
        return condition["contains"] in probe.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return False


def _compare_recipe(name: str, spec: dict, found: dict, mod_id: str) -> list[str]:
    drift = []
    want_prereq, want_recipe = _expected(spec, mod_id)
    if found["prerequisites"] != want_prereq:
        drift.append(
            f"{name}: prerequisites are '{found['prerequisites']}', "
            f"expected '{want_prereq}'"
        )
    if found["recipe"] != want_recipe:
        drift.append(
            f"{name}: recipe differs from the contract "
            f"(has {len(found['recipe'])} line(s), expected {len(want_recipe)})"
        )
    return drift


def check_member(member_dir: pathlib.Path, mod_id: str, contract: dict
                 ) -> tuple[list[str], list[str]]:
    """(drift, notes) for one member. `member_dir` is <root>/<id>."""
    drift: list[str] = []
    notes: list[str] = []

    makefile = member_dir / "Makefile"
    try:
        text = makefile.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ([], ["no Makefile found — cannot check"])

    targets, help_lines, phony = parse_makefile(text)
    governed: list[str] = []

    for spec in contract["universal"]:
        name = spec["target"]
        governed.append(name)
        if name not in targets:
            drift.append(f"{name}: target is missing")
            continue
        drift.extend(_compare_recipe(name, spec, targets[name], mod_id))

    for spec in contract["conditional"]:
        name = spec["target"]
        governed.append(name)
        holds = _condition_holds(member_dir, spec["requiredWhen"])
        if name not in targets:
            if holds:
                condition = spec["requiredWhen"]
                drift.append(
                    f"{name}: target is missing while {condition['file']} "
                    f"has '{condition['contains']}' — {spec['because']}"
                )
            else:
                notes.append(f"{name}: absent, and not wired in this member")
            continue
        drift.extend(_compare_recipe(name, spec, targets[name], mod_id))

    drift.extend(_check_help(targets, help_lines, contract, governed))
    drift.extend(_check_phony(targets, phony))

    for name in sorted(targets):
        if name not in governed and name != "help":
            notes.append(f"{name}: target is not in the contract")

    return (drift, notes)


def _check_help(targets: dict, help_lines: list[tuple[str, str]], contract: dict,
                governed: list[str]) -> list[str]:
    """help must project the manifest's descriptions over the targets present."""
    if "help" not in targets:
        return ["help: target is missing"]

    described = {name: text for name, text in help_lines}
    canonical = {
        spec["target"]: spec["help"]
        for spec in contract["universal"] + contract["conditional"]
    }

    drift = []
    for name, text in help_lines:
        if name in canonical and text != canonical[name]:
            drift.append(
                f"help: describes {name} as '{text}', "
                f"expected '{canonical[name]}'"
            )
        if name not in targets:
            drift.append(f"help: lists {name}, which this Makefile does not define")

    for name in governed:
        if name in targets and name not in described:
            drift.append(f"help: does not list {name}, which this Makefile defines")

    listed = [name for name, _ in help_lines if name in contract["helpOrder"]]
    expected_order = [name for name in contract["helpOrder"] if name in listed]
    if listed != expected_order:
        drift.append(
            f"help: lists targets in the order {listed}, expected {expected_order}"
        )

    return drift


def _check_phony(targets: dict, phony: list[str]) -> list[str]:
    """A target absent from .PHONY is shadowed by any file of the same name."""
    if not phony:
        return [".PHONY: no .PHONY declaration"]
    return [
        f".PHONY: does not list {name}, so a file of that name shadows the target"
        for name in sorted(targets)
        if name not in phony
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="..",
        help="directory holding the member checkouts as <root>/<id> (default: ..)",
    )
    parser.add_argument("--members", default="members.json")
    parser.add_argument("--contract", default="makefile-targets.json")
    args = parser.parse_args(argv)

    contract = load_contract(pathlib.Path(args.contract))
    ids = member_ids(pathlib.Path(args.members))
    root = pathlib.Path(args.root)

    drift: list[str] = []
    notes: list[str] = []
    checked_members = 0

    for mid in ids:
        member_dir = root / mid
        if not member_dir.is_dir():
            notes.append(f"skip: {mid} not checked out at {member_dir}")
            continue
        checked_members += 1
        member_drift, member_notes = check_member(member_dir, mid, contract)
        for reason in member_drift:
            drift.append(f"drift: {mid} — {reason}")
        for note in member_notes:
            notes.append(f"note: {mid} — {note}")

    for note in notes:
        print(note, file=sys.stderr)

    if drift:
        for line in drift:
            print(line, file=sys.stderr)
        print(
            f"\n{len(drift)} Makefile target finding(s) across {checked_members} "
            "member(s). Fix the member Makefile(s) or update "
            "makefile-targets.json.",
            file=sys.stderr,
        )
        return 1

    if checked_members == 0:
        print("no members checked out — nothing to compare.")
        return 0
    print(f"all member Makefiles match the target contract "
          f"({checked_members} member(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
