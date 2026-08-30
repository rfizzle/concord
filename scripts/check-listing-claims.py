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

It reads `site/pages/*.json` too. The website publishes the same claims, and
every phantom integration found in the listings shipped there as well — a check
that reads only the two Markdown files covers half the surface. Page claims
report rather than fail: a page is prose, and its backing code may live in a
sibling repo a member's CI has not checked out. It does fail a mod whose pages
still say it is unreleased once a `v*` tag exists — that one is unambiguous,
and cultivation and distillation both told players "not yet released" for hours
after publishing with nothing to catch it.

Exits non-zero on a phantom integration, an unlisted block or advancement, a
stale unreleased claim, or a short description over Modrinth's 256-char cap.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ("site/listing-modrinth.md", "site/listing-curseforge.md")
SUMMARY = "site/listing-summary.txt"
SITE_PAGES = "site/pages"

# A released mod telling players it is not released. This is a curated list of
# phrasings actually found on live pages, not a general pattern, and that is a
# deliberate retreat: matching the *shape* (a negation near a shipping word)
# was tried and found one false positive for every real hit — mercantile's "no
# resource-pack download and no surprises", its "no-shared-jar" architecture
# note, prosperity's and tribulation's "no Forge/NeoForge build". A blocking
# gate that cries wolf gets switched off, so precision wins over recall here.
#
# The cost is that the list lags: three review rounds each found this same lie
# in wording the previous list missed. Add to it when that happens rather than
# generalising it — and read the pages, because this rule will never be the
# thing that finds a new phrasing first.
UNRELEASED_CLAIM = re.compile(
    r"not yet released|nothing is released|no download today|in development"
    r"|being built against|there is nothing to install"
    r"|not yet a shipped|not a shipped jar|has not shipped"
    r"|no version has been tagged|no build is published"
    r"|no published build|this page describes the first release", re.I)
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


def load_taglines(members_file=None):
    """Map member display name -> tagline, for suite-row recognition."""
    for candidate in (members_file, ROOT / "members.json",
                      Path(".concord/members.json"), Path("../concord/members.json")):
        if not candidate or not Path(candidate).is_file():
            continue
        registry = json.loads(Path(candidate).read_text(encoding="utf-8"))
        return {(m.get("name") or m["id"].title()): m.get("tagline")
                for m in registry.get("members") or [] if m.get("id")}
    return {}


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


def strip_suite_links(text, members=None):
    """Blank the suite strip's rows and boilerplate, keeping every other
    sentence — including any that happens to sit in the same section.

    A suite row is a sibling's name beside its registered tagline, and the
    markup varies by surface: `- [Meridian](url) — Chart your enchantments.` in
    Markdown, `<strong class='text-bone'>Meridian</strong> — Chart your
    enchantments.` in the site JSON. Matching the tagline rather than the markup
    covers both, and it is exact: a row only counts as suite identity when it
    carries the tagline members.json records. Anything else that names a
    sibling is prose, and prose about a sibling is a claim.
    """
    text = SUITE_BULLET.sub("", text)
    for name, tagline in (members or {}).items():
        if not tagline:
            continue
        text = re.sub(rf"[^\n]*{re.escape(name)}[^\n]{{0,80}}?{re.escape(tagline)}",
                      "", text)
    return SUITE_BOILERPLATE.sub("", text)


def released(repo):
    """Has this mod ever shipped? A `v*` tag is the suite's source of version
    truth — the release workflow triggers on exactly that."""
    try:
        proc = subprocess.run(["git", "tag", "--list", "v*"], cwd=repo,
                              capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


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
    a false positive here only means we stay quiet, never that we accuse.

    Also looks in the sibling's own checkout when one sits alongside this repo,
    because an integration is often implemented on the other side: tribulation's
    pages say its HUD "stacks cleanly with HUDs from Meridian, Mercantile", and
    that is true — mercantile's ReputationHudOverlay is what accounts for it,
    and tribulation's source says nothing. A member's CI has no sibling
    checkouts, which is one reason a page claim reports rather than fails.
    """
    peer = repo.resolve().parent / sibling
    if peer.is_dir() and peer != repo.resolve():
        own = mod_id(repo)
        for tree in ("src/main/java", "src/client/java", "src/main/resources"):
            base = peer / tree
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix not in (".java", ".json"):
                    continue
                if path.name == "fabric.mod.json":
                    continue
                try:
                    if own and own in path.read_text(encoding="utf-8", errors="ignore"):
                        return f"{sibling}/{path.relative_to(peer)}"
                except OSError:
                    continue

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
    taglines = load_taglines()
    body = normalize(strip_suite_links(primary.read_text(encoding="utf-8"), taglines))
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

    # 3. Phantom integrations on the website, which publishes the same claims.
    #    Each of the 11 found in the listings shipped here too, so a check that
    #    reads only site/listing-*.md leaves half the surface uncovered.
    for page in sorted((repo / SITE_PAGES).glob("*.json")):
        try:
            text = normalize(strip_suite_links(page.read_text(encoding="utf-8"), taglines))
        except OSError:
            continue
        for sibling, name in sorted(members.items()):
            if sibling == modid or not re.search(rf"\b{re.escape(name)}\b", text):
                continue
            # A comparison ("how is this different from X") is not a claim.
            if re.search(rf"different from {re.escape(name)}|"
                         rf"{re.escape(name)} owns\b", text, re.I):
                continue
            if not integration_evidence(repo, sibling):
                # Reported, not failed. A page is prose — "the same approach
                # Prosperity's indicators use" compares a technique rather than
                # promising behaviour — and the backing code may live in a
                # sibling checkout that a member's CI does not have.
                warnings.append(
                    f"{SITE_PAGES}/{page.name}: names {name} outside the suite list; "
                    f"the repo references '{sibling}' nowhere — check it is not "
                    f"promising an integration that does not exist")

    # 4. A released mod still telling players it is unreleased.
    if released(repo):
        for path in list(listings.values()) + sorted((repo / SITE_PAGES).glob("*.json")):
            try:
                hit = UNRELEASED_CLAIM.search(normalize(path.read_text(encoding="utf-8")))
            except OSError:
                continue
            # "no resource-pack download required" is a feature, not a release
            # state. A negation about a *requirement* is the common innocent
            # shape, so judge the words around the match before accusing.
            if hit and not re.search(r"\b(required|needed|necessary|to install)\b",
                                     hit.string[hit.start():hit.end() + 30], re.I):
                errors.append(
                    f"{path.relative_to(repo)}: says \"{hit.group(0)}\" but the repo "
                    f"has a release tag — the page is telling players a shipped mod "
                    f"is not out yet")

    # 5. Modrinth caps the short description.
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
