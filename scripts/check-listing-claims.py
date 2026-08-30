#!/usr/bin/env python3
"""Check a member's store listing against what the mod actually ships.

`site/listing-modrinth.md` syncs live to the Modrinth project description on
every push to master, and `site/listing-curseforge.md` is pasted into
CurseForge by hand. Both are the first thing a player reads. Three consecutive
conformance sweeps found a listing describing a different mod than the one in
the repo, in both directions:

  - distillation undercounted its antidotes ("four more" for eight);
  - cultivation omitted four shipped features, including a craftable item with
    its own advancement;
  - instinct omitted six of ten features, a craftable block, an item and five
    advancements — and claimed four sibling integrations that exist in neither
    codebase.

Prose can summarise, so this does not try to grade the writing. It checks the
two claims a machine can settle from the repo:

  1. **Phantom integrations.** A sibling named outside the suite strip reads as
     shipped behaviour ("with X, Y happens"). Require evidence: a `compat/<id>/`
     package, a `data/<id>/` tree, a `depends` entry, or any source reference.
     A bare `suggests` is deliberately not evidence — every member suggests
     every sibling at `*`, so it would excuse the very claims this catches. The suite strip itself ("Part of Concord" / "Companion mods")
     lists every sibling by design and is excluded.
  2. **Unlisted content.** Every registered block, item, and advancement has a
     display name in the lang file, so a listing can be checked against the
     inventory it is describing.

     Blocks fail: seven of eight members name every block they register, and
     the eighth (meridian) names 24 of 29 — so this codifies what the suite
     already does rather than imposing a new rule. Items report without
     failing; they are numerous and often incidental.

     Advancements are judged against the listing's own choice. Only instinct
     ships an `## Advancements` section, and there a missing entry is a real
     hole in a list that claims to be complete, so it fails. A listing that
     never enumerates advancements is making a legitimate editorial call and is
     left alone — flagging all 65 across the suite would be inventing a
     standard, not enforcing one.

    python3 scripts/check-listing-claims.py                  # this repo
    python3 scripts/check-listing-claims.py --root ../instinct
    python3 scripts/check-listing-claims.py --root .. --all-members

Exits non-zero on a phantom integration, an unlisted block or advancement, or a
short description over Modrinth's 256-character cap.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ("site/listing-modrinth.md", "site/listing-curseforge.md")
SUMMARY = "site/listing-summary.txt"
MODRINTH_SUMMARY_CAP = 256

# The suite strip lists every sibling by design, so its bullets are not claims:
#   - [Meridian](https://meridian.rfizzle.com) — Chart your enchantments.
# Excluding the whole *section* would be too blunt. Instinct's four phantom
# integrations sat inside its "Part of Concord" section, in an "**Enhanced by**
# … **Mercantile** — butchers sell Vet Kits" sentence — so a section-level
# exclusion silently passed the exact case this check exists to catch. Drop the
# link bullets and the boilerplate line; judge every other sentence.
SUITE_BULLET = re.compile(
    r"^\s*[-*]\s*\[[^\]]+\]\(https?://[^)]*rfizzle\.com[^)]*\)\s*[—-].*$", re.M)
SUITE_BOILERPLATE = re.compile(
    r"^.*\bpart of \[?Concord\]?.*$|^.*\bInstall any, combine all\b.*$", re.I | re.M)
ADVANCEMENTS_SECTION = re.compile(r"^##\s+advancements\s*$", re.I | re.M)


def load_members(members_file=None):
    """Map member id -> display name, from the hub registry."""
    for candidate in (members_file, ROOT / "members.json",
                      Path(".concord/members.json"), Path("../concord/members.json")):
        if not candidate or not Path(candidate).is_file():
            continue
        registry = json.loads(Path(candidate).read_text(encoding="utf-8"))
        return {m["id"]: m.get("name") or m["id"].title()
                for m in registry.get("members") or [] if m.get("id")}
    return {}


def strip_suite_links(text):
    """Blank the suite strip's link bullets and boilerplate, keeping every
    other sentence — including any that happens to sit in the same section."""
    text = SUITE_BULLET.sub("", text)
    return SUITE_BOILERPLATE.sub("", text)


def normalize(text):
    """Flatten a listing for phrase matching.

    A display name is one phrase; the listing is hard-wrapped Markdown, so
    "Best in Show" can arrive as "**Best in\nShow**" and a raw search misses a
    name that is plainly there. Collapse whitespace and drop emphasis markers
    so the comparison is about words, not typography.
    """
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", text))


def names(listing, display):
    """Is `display` named in `listing`?

    A plain phrase match is not enough. A listing legitimately compresses a
    family of blocks that share a suffix — meridian writes

        Shelf of Seabound / Hellbound / End-Fused Rectification

    for three registered blocks, and each is genuinely named there. So fall
    back to: do this name's words appear, in order, inside a single line?
    That accepts the compressed form and still refuses a name the page never
    mentions. The fallback only ever forgives, so it cannot invent a finding.
    """
    if re.search(rf"\b{re.escape(display)}\b", listing, re.I):
        return True
    words = [re.escape(w) for w in display.split()]
    inline = r"\b" + r"\b.{0,40}?\b".join(words) + r"\b"
    return any(re.search(inline, line, re.I) for line in listing.splitlines())


def mod_id(repo):
    for path in sorted(repo.glob("src/main/resources/fabric.mod.json")):
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("id")
        except (OSError, json.JSONDecodeError):
            return None
    return None


def lang_entries(repo, modid):
    """Registered content by kind, from the lang file: {kind: {key: display}}."""
    path = repo / f"src/main/resources/assets/{modid}/lang/en_us.json"
    if not path.is_file():
        return {}
    try:
        lang = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out = {"block": {}, "item": {}, "advancement": {}}
    for key, value in lang.items():
        parts = key.split(".")
        # Exactly three segments is the display name: `item.<mod>.<name>`.
        # Anything longer is a sub-key hanging off it — tooltips, hold-shift
        # lines, use messages — which are not content a listing owes a mention.
        if len(parts) == 3 and parts[1] == modid and parts[0] in ("block", "item"):
            out[parts[0]][key] = value
        # advancements.<mod>.<name>.title — skip root, whose title is the mod name
        elif (key.startswith(f"advancements.{modid}.") and key.endswith(".title")
              and parts[2] != "root"):
            out["advancement"][key] = value
    return out


def integration_evidence(repo, sibling):
    """Does this repo actually reference `sibling`? Cheap, deliberately broad —
    a false positive here only means we stay quiet, never that we accuse."""
    if (repo / "src/main/java").exists():
        for path in repo.rglob(f"**/compat/{sibling}"):
            if path.is_dir():
                return f"compat/{sibling}/"
    for data in repo.glob(f"src/main/resources/data/{sibling}"):
        if data.is_dir():
            return f"data/{sibling}/"
    for data in repo.glob(f"src/main/generated/data/{sibling}"):
        if data.is_dir():
            return f"generated data/{sibling}/"
    # A bare `suggests` entry is NOT evidence. It declares soft compatibility,
    # which every member grants every sibling at `*`; it says nothing about an
    # integration existing. Distillation suggests tribulation and its listing
    # claimed "its shard debuffs gain brewable antidotes of their own" — no code
    # anywhere registers one, and counting the entry hid that. `depends` is
    # different: a hard dependency is only ever declared for real coupling.
    meta = repo / "src/main/resources/fabric.mod.json"
    if meta.is_file():
        try:
            parsed = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            parsed = {}
        if sibling in (parsed.get("depends") or {}):
            return "fabric.mod.json depends"
    for tree in ("src/main/java", "src/client/java", "src/main/resources"):
        base = repo / tree
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in (".java", ".json"):
                continue
            # Handled explicitly above. Left in the generic scan it re-admits a
            # bare `suggests` entry as a plain string match, which is the hole
            # the explicit check was just narrowed to close.
            if path.name == "fabric.mod.json":
                continue
            try:
                if sibling in path.read_text(encoding="utf-8", errors="ignore"):
                    return str(path.relative_to(repo))
            except OSError:
                continue
    return None


def check_repo(repo, members, verbose=False):
    """Returns (errors, warnings) as lists of strings."""
    repo = Path(repo)
    errors, warnings = [], []
    modid = mod_id(repo)
    if not modid:
        return errors, warnings

    listings = {name: (repo / name) for name in LISTINGS
                if (repo / name).is_file()}
    if not listings:
        return errors, warnings

    # 1. Phantom integrations, judged on the Modrinth copy (the one that
    #    auto-publishes); the two files are meant to be near-identical.
    primary = listings.get(LISTINGS[0]) or next(iter(listings.values()))
    body = normalize(strip_suite_links(primary.read_text(encoding="utf-8")))
    for sibling, name in sorted(members.items()):
        if sibling == modid:
            continue
        if not re.search(rf"\b{re.escape(name)}\b", body):
            continue
        evidence = integration_evidence(repo, sibling)
        if evidence:
            if verbose:
                print(f"    {name}: integration claim backed by {evidence}")
        else:
            errors.append(
                f"{primary.name}: claims an integration with {name}, but the repo "
                f"references '{sibling}' nowhere — no compat package, no data tree, "
                f"no dependency entry, no source mention")

    # 2. Content that ships but is never named.
    entries = lang_entries(repo, modid)
    raw = {name: path.read_text(encoding="utf-8") for name, path in listings.items()}
    texts = {name: normalize(text) for name, text in raw.items()}
    # A listing that enumerates advancements owes the full set; one that never
    # mentions them is summarising, which is its right.
    enumerates_advancements = any(ADVANCEMENTS_SECTION.search(t) for t in raw.values())
    if not enumerates_advancements:
        entries.pop("advancement", None)
    for kind, bucket in entries.items():
        for key, display in sorted(bucket.items(), key=lambda kv: kv[1]):
            needle = normalize(display)
            missing = [n for n, t in texts.items() if not names(t, needle)]
            if not missing:
                continue
            where = ", ".join(sorted(Path(n).name for n in missing))
            line = f"{where}: ships {kind} \"{display}\" ({key}), never named"
            (errors if kind in ("block", "advancement") else warnings).append(line)

    # 3. Modrinth caps the short description.
    summary = repo / SUMMARY
    if summary.is_file():
        text = " ".join(summary.read_text(encoding="utf-8").split())
        if len(text) > MODRINTH_SUMMARY_CAP:
            errors.append(f"{SUMMARY}: {len(text)} chars, over Modrinth's "
                          f"{MODRINTH_SUMMARY_CAP}-character cap")
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="repo to check (default: cwd)")
    ap.add_argument("--all-members", action="store_true",
                    help="treat --root as the parent of every member checkout")
    ap.add_argument("--members-file", default=None,
                    help="path to members.json (default: the hub's own)")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="also print the evidence backing each accepted claim")
    args = ap.parse_args(argv)

    members = load_members(args.members_file)
    root = Path(args.root)
    repos = ([root / m for m in sorted(members) if (root / m).is_dir()]
             if args.all_members else [root])

    failed = False
    for repo in repos:
        errors, warnings = check_repo(repo, members, args.verbose)
        if errors or warnings or args.verbose:
            print(f"{repo.name or repo}:")
        for line in errors:
            print(f"  error: {line}")
        for line in warnings:
            print(f"  warning: {line}")
        if not errors and not warnings:
            if args.verbose:
                print("  listing matches what the mod ships")
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
