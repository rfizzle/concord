#!/usr/bin/env python3
"""Check each member repo's Makefile against the shared concord.mk contract.

The universal Makefile targets (`build`, `test`, `coverage`, `ci`, `release`, ...)
live in one hub-owned file, propagate/concord.mk, that the sync PR copies verbatim
into every member. A member's own Makefile does `include concord.mk` and adds only
its member-specific targets. That uniformity is what lets any agent or human drop
into any member repo and know that `make coverage` means the merged report and
`make release` only tags. It needs a checker because every way it breaks is quiet:
a Makefile that stops including the file still builds and tests fine, and a
redefined target silently shadows the shared recipe.

What counts as drift, per member:

  - the Makefile does not `include concord.mk`
  - concord.mk is missing from the member, or differs from the hub's copy
  - the Makefile defines a target concord.mk owns (a redefinition shadows or
    overrides the shared recipe; the fix goes in the hub, not the member)

And once, for the hub itself: makefile-targets.json must list exactly the targets
propagate/concord.mk defines, so the contract and the file cannot diverge.

Everything else is a note: a target this contract says nothing about (a member is
free to add targets), or a member not checked out. The contract is a floor, not a
ceiling.

Member ids come from members.json; each member repo is read from <root>/<id>/.
Locally that is the sibling checkout (../<member>, the default); the scheduled
makefile-drift workflow mirrors each member's Makefile and concord.mk into a temp
tree and points --root at it.

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

# A rule line: one or more target names, then a single or double colon that is not
# part of `:=`/`::=`. Variable assignments (`X := 1`, `X ?= 1`) and recipe lines
# (tab-prefixed) never match.
RULE_RE = re.compile(r"^([^\s:#=\t.$%][^:#=]*?)\s*::?(?![=:])")
INCLUDE_RE = re.compile(r"^-?include\s+(\S+)\s*$")


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
    ids = [m.get("id") for m in data.get("members", [])]
    if not all(ids):
        print("error: members.json has an entry with no 'id'", file=sys.stderr)
        raise SystemExit(2)
    return ids


def _malformed(detail: str) -> "SystemExit":
    print(f"error: makefile-targets.json {detail}", file=sys.stderr)
    return SystemExit(2)


def load_contract(path: pathlib.Path) -> dict:
    """Load and validate the contract, so a malformed one fails with a clean
    message rather than a KeyError from deep inside a comparison."""
    data = _load_json(path, "makefile-targets.json")
    if not isinstance(data.get("include"), str) or not data["include"]:
        raise _malformed("has no 'include' file name")
    targets = data.get("targets")
    if not isinstance(targets, list) or not targets or not all(
        isinstance(t, str) and t for t in targets
    ):
        raise _malformed("has no 'targets' list of target names")
    if len(set(targets)) != len(targets):
        raise _malformed("lists a target more than once")
    return data


def _join_continuations(lines: list[str]) -> list[str]:
    """Fold backslash-continued lines into one, the way make reads them."""
    joined: list[str] = []
    pending: str | None = None
    for line in lines:
        current = line if pending is None else pending + " " + line.lstrip()
        if current.endswith("\\"):
            pending = current[:-1].rstrip()
            continue
        joined.append(current)
        pending = None
    if pending is not None:
        joined.append(pending)
    return joined


def parse_makefile(text: str) -> tuple[set[str], list[str]]:
    """(defined target names, included file names) from Makefile source.

    Recipe lines (tab-prefixed) and comments are skipped. Special targets such as
    `.PHONY` and pattern rules are not targets for this purpose.
    """
    targets: set[str] = set()
    includes: list[str] = []
    for line in _join_continuations(text.splitlines()):
        if line.startswith("\t") or line.lstrip().startswith("#"):
            continue
        included = INCLUDE_RE.match(line)
        if included:
            includes.append(included.group(1))
            continue
        matched = RULE_RE.match(line)
        if matched:
            for name in matched.group(1).split():
                if not name.startswith(".") and "%" not in name and "$" not in name:
                    targets.add(name)
    return targets, includes


def check_hub(contract: dict, hub_text: str) -> list[str]:
    """Drift between makefile-targets.json and the targets propagate/concord.mk defines."""
    defined, _ = parse_makefile(hub_text)
    listed = set(contract["targets"])
    drift = []
    for name in sorted(defined - listed):
        drift.append(f"hub: {contract['include']} defines '{name}', which makefile-targets.json does not list")
    for name in sorted(listed - defined):
        drift.append(f"hub: makefile-targets.json lists '{name}', which {contract['include']} does not define")
    return drift


def check_member(member_dir: pathlib.Path, contract: dict, hub_bytes: bytes | None
                 ) -> tuple[list[str], list[str]]:
    """(drift, notes) for one member. `member_dir` is <root>/<id>."""
    drift: list[str] = []
    notes: list[str] = []
    include = contract["include"]

    makefile = member_dir / "Makefile"
    try:
        text = makefile.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ([], ["no Makefile found — cannot check"])
    except (UnicodeDecodeError, IsADirectoryError, PermissionError) as exc:
        return ([], [f"Makefile is unreadable ({type(exc).__name__}) — cannot check"])

    targets, includes = parse_makefile(text)

    if include not in includes:
        drift.append(f"Makefile does not `include {include}`")

    shared = member_dir / include
    try:
        member_bytes = shared.read_bytes()
    except FileNotFoundError:
        drift.append(f"{include} is missing — it is propagated from the hub")
    except (IsADirectoryError, PermissionError) as exc:
        drift.append(f"{include} is unreadable ({type(exc).__name__})")
    else:
        if hub_bytes is not None and member_bytes != hub_bytes:
            drift.append(
                f"{include} differs from the hub's propagate/{include} — "
                "it is hub-owned; change it in the hub, not the member"
            )

    owned = set(contract["targets"])
    for name in sorted(targets & owned):
        drift.append(
            f"{name}: redefined in the Makefile, but {include} owns it — "
            "change the hub's recipe instead of overriding it"
        )

    for name in sorted(targets - owned):
        notes.append(f"{name}: member-specific target (not in the contract)")

    return (drift, notes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default="..",
        help="directory holding the member checkouts as <root>/<id> (default: ..)",
    )
    parser.add_argument("--members", default="members.json")
    parser.add_argument("--contract", default="makefile-targets.json")
    parser.add_argument(
        "--hub-file",
        default=None,
        help="the hub's concord.mk (default: propagate/<include> next to the contract)",
    )
    args = parser.parse_args(argv)

    contract_path = pathlib.Path(args.contract)
    contract = load_contract(contract_path)
    ids = member_ids(pathlib.Path(args.members))
    root = pathlib.Path(args.root)

    hub_path = (
        pathlib.Path(args.hub_file)
        if args.hub_file
        else contract_path.resolve().parent / "propagate" / contract["include"]
    )
    try:
        hub_bytes = hub_path.read_bytes()
    except FileNotFoundError:
        print(f"error: hub file not found at {hub_path}", file=sys.stderr)
        raise SystemExit(2)

    drift: list[str] = []
    notes: list[str] = []
    checked_members = 0

    for reason in check_hub(contract, hub_bytes.decode("utf-8")):
        drift.append(f"drift: {reason}")

    for mid in ids:
        member_dir = root / mid
        if not member_dir.is_dir():
            notes.append(f"skip: {mid} not checked out at {member_dir}")
            continue
        checked_members += 1
        member_drift, member_notes = check_member(member_dir, contract, hub_bytes)
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
            f"\n{len(drift)} Makefile finding(s) across {checked_members} "
            f"member(s). Fix the member Makefile(s), or the hub's {contract['include']} "
            "and makefile-targets.json together.",
            file=sys.stderr,
        )
        return 1

    if checked_members == 0:
        print("no members checked out — nothing to compare.")
        return 0
    print(f"all member Makefiles include {contract['include']} and redefine none of its "
          f"targets ({checked_members} member(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
