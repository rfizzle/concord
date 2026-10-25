#!/usr/bin/env python3
"""Generate the Concord suite status dashboard from public APIs.

Reads members.json and queries the GitHub API (releases, latest CI run on
master, open issue count) and the Modrinth API (downloads, followers).
Public reads only — GITHUB_TOKEN, when present, merely raises the rate limit.
Every fetch is best-effort per member: an unreachable endpoint, an unpublished
Modrinth listing (404), or a repo without releases becomes null data, never a
failed run, so the site build always has something to render.

A member's status is derived from its GitHub releases (newest non-draft,
pre-releases included): a stable release means "released", a pre-release means
"beta", no release means "in-development".

The site build runs this before eleventy; the outputs are not committed, except
that the landing page's committed suite-status blocks are the fallback shape.
Writes three files:

    site/status.json          raw per-member data + collection totals
    site/pages/status.json    the dashboard page, template block schema only
    site/pages/index.json     refreshes the blocks of the landing section whose
                              id is "suite-status" (file untouched when the
                              section is absent or already current)

Run from the concord repo root:

    python3 scripts/gen-status.py
"""

from __future__ import annotations

import datetime
import html
import http.client
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

MEMBERS_JSON = pathlib.Path("members.json")
STATUS_JSON = pathlib.Path("site/status.json")
STATUS_PAGE_JSON = pathlib.Path("site/pages/status.json")
INDEX_PAGE_JSON = pathlib.Path("site/pages/index.json")

OWNER = "rfizzle"
GITHUB_API = "https://api.github.com"
MODRINTH_API = "https://api.modrinth.com/v2"
USER_AGENT = "rfizzle/concord gen-status (+https://github.com/rfizzle/concord)"
TIMEOUT = 30

DASH = "—"
INDEX_STATUS_SECTION_ID = "suite-status"
LINK_CLASS = "text-accent hover:text-accent2 underline"


def http_fetch(url: str, headers: dict[str, str] | None = None) -> tuple[int, object]:
    """GET a JSON endpoint. Returns (http_status, parsed_body_or_None); never
    raises — a network or parse failure comes back as (0, None) or (code, None)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, None
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ValueError, OSError):
        return 0, None


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _date(iso: str | None) -> str | None:
    """The date part of an ISO timestamp ("2026-07-01T12:43:41Z" → "2026-07-01")."""
    return iso[:10] if iso else None


def latest_release(releases: list) -> dict | None:
    """The newest non-draft release (pre-releases included), as
    {tag, date, prerelease}. The API lists newest first."""
    for rel in releases:
        if isinstance(rel, dict) and rel.get("tag_name") and not rel.get("draft"):
            return {
                "tag": rel["tag_name"],
                "date": _date(rel.get("published_at") or rel.get("created_at")),
                "prerelease": bool(rel.get("prerelease")),
            }
    return None


def derive_status(release: dict | None) -> str:
    """released (stable tag) / beta (pre-release only) / in-development (none)."""
    if not release:
        return "in-development"
    return "beta" if release["prerelease"] else "released"


def fetch_member(member: dict, fetch) -> dict:
    """Best-effort live status for one member; missing data becomes None."""
    mid = member["id"]
    repo = f"{OWNER}/{mid}"
    gh = github_headers()

    release = None
    code, data = fetch(f"{GITHUB_API}/repos/{repo}/releases?per_page=10", gh)
    if code == 200 and isinstance(data, list):
        release = latest_release(data)

    ci = None
    code, data = fetch(
        f"{GITHUB_API}/repos/{repo}/actions/workflows/ci.yml/runs"
        "?branch=master&per_page=1&exclude_pull_requests=true",
        gh,
    )
    if code == 200 and isinstance(data, dict) and data.get("workflow_runs"):
        run = data["workflow_runs"][0]
        ci = {
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "date": _date(run.get("updated_at")),
        }

    open_issues = None
    query = urllib.parse.urlencode(
        {"q": f"repo:{repo} type:issue state:open", "per_page": 1}
    )
    code, data = fetch(f"{GITHUB_API}/search/issues?{query}", gh)
    if code == 200 and isinstance(data, dict) and isinstance(data.get("total_count"), int):
        open_issues = data["total_count"]

    modrinth = None
    store = (member.get("store") or {}).get("modrinth") or {}
    lookup = store.get("id") or store.get("slug")
    if lookup:
        code, data = fetch(f"{MODRINTH_API}/project/{urllib.parse.quote(lookup, safe='')}", None)
        if code == 200 and isinstance(data, dict):
            modrinth = {
                "slug": data.get("slug") or store.get("slug"),
                "downloads": data.get("downloads"),
                "followers": data.get("followers"),
            }

    return {
        "id": mid,
        "name": member["name"],
        "url": member["url"],
        "repo": repo,
        "status": derive_status(release),
        "release": release,
        "ci": ci,
        "openIssues": open_issues,
        "modrinth": modrinth,
    }


def build_status(members_doc: dict, fetch) -> dict:
    """The status document body (everything except the `generated` stamp)."""
    members = [fetch_member(m, fetch) for m in members_doc.get("members", [])]
    downloads = [
        m["modrinth"]["downloads"]
        for m in members
        if m["modrinth"] and isinstance(m["modrinth"].get("downloads"), int)
    ]
    followers = [
        m["modrinth"]["followers"]
        for m in members
        if m["modrinth"] and isinstance(m["modrinth"].get("followers"), int)
    ]
    issues = [m["openIssues"] for m in members if isinstance(m["openIssues"], int)]
    totals = {
        "members": len(members),
        "released": sum(1 for m in members if m["status"] == "released"),
        "downloads": sum(downloads) if downloads else None,
        "followers": sum(followers) if followers else None,
        "openIssues": sum(issues) if issues else None,
    }
    return {"totals": totals, "members": members}


def fmt_count(n: object) -> str:
    return f"{n:,}" if isinstance(n, int) else DASH


def stat_cards(status: dict) -> dict:
    t = status["totals"]
    return {
        "type": "cards",
        "mdColumns": 3,
        "lgColumns": 3,
        "items": [
            {
                "title": fmt_count(t["downloads"]),
                "html": ["Downloads across the collection"],
            },
            {
                "title": f"{t['released']} of {t['members']}",
                "html": ["Members released"],
            },
            {
                "title": fmt_count(t["openIssues"]),
                "html": ["Open issues across the suite"],
            },
        ],
    }


STATUS_CELLS = {
    "released": "<span class='text-accent'>released</span>",
    "beta": "<span class='text-accent'>beta</span>",
    "in-development": "<span class='text-ash'>in development</span>",
}


def member_row(m: dict) -> list[str]:
    name = f"<a class='{LINK_CLASS}' href='{m['url']}'>{m['name']}</a>"
    status = STATUS_CELLS[m["status"]]
    # tag and slug arrive from API responses (member repos and their Modrinth
    # projects are owner-controlled, but escape anyway — the template renders
    # cells with | safe).
    version = html.escape(m["release"]["tag"]) if m["release"] else DASH
    released = (m["release"] or {}).get("date") or DASH
    if m["ci"]:
        actions = f"https://github.com/{m['repo']}/actions/workflows/ci.yml"
        ci = (
            f"<a href='{actions}'>"
            f"<img class='inline h-5' src='{actions}/badge.svg?branch=master'"
            f" alt='{m['name']} CI status'></a>"
        )
    else:
        ci = DASH
    if m["modrinth"] and isinstance(m["modrinth"].get("downloads"), int):
        slug = html.escape(str(m["modrinth"]["slug"]))
        downloads = (
            f"<a class='{LINK_CLASS}' href='https://modrinth.com/mod/{slug}'>"
            f"{m['modrinth']['downloads']:,}</a>"
        )
    else:
        downloads = DASH
    issues = (
        f"<a class='{LINK_CLASS}' href='https://github.com/{m['repo']}/issues'>"
        f"{m['openIssues']:,}</a>"
        if isinstance(m["openIssues"], int)
        else DASH
    )
    return [name, status, version, released, ci, downloads, issues]


def render_status_page(status: dict) -> dict:
    table = {
        "type": "table",
        "nowrapHeaders": True,
        "headers": [
            "Member", "Status", "Version", "Released",
            "CI", "Downloads", "Open issues",
        ],
        "rows": [member_row(m) for m in status["members"]],
        "note": (
            f"Downloads count each member's Modrinth listing; members without a public "
            f"listing yet show {DASH}. Refreshed nightly from the GitHub and Modrinth "
            f"APIs · generated {status['generated']}."
        ),
    }
    return {
        "nav": "Status",
        "metaTitle": "Concord — Suite Status",
        "metaDescription": (
            "Live health for every Concord member mod — latest release, CI state, "
            "downloads, and open issues, refreshed nightly."
        ),
        "title": "Suite status",
        "lede": (
            "Every member's latest release, CI state, downloads, and open work — "
            "one view, refreshed nightly."
        ),
        "width": "6xl",
        "sections": [
            {"blocks": [stat_cards(status)]},
            {"title": "Members", "blocks": [table]},
        ],
    }


def index_status_blocks(status: dict) -> list[dict]:
    note = (
        "Per-member detail — versions, CI, downloads, open work — on the "
        f"<a class='{LINK_CLASS}' href='/status.html'>status page</a>."
    )
    return [stat_cards(status), {"type": "note", "html": note, "center": True}]


def patch_index(index_doc: dict, status: dict) -> bool:
    """Replace the blocks of the id-marked landing section. Returns True when
    the document changed; a missing section or current blocks are a no-op."""
    for section in index_doc.get("sections", []):
        if section.get("id") == INDEX_STATUS_SECTION_ID:
            blocks = index_status_blocks(status)
            if section.get("blocks") != blocks:
                section["blocks"] = blocks
                return True
            return False
    return False


def write_json(path: pathlib.Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    if not MEMBERS_JSON.exists():
        print("members.json not found — run from the concord repo root.", file=sys.stderr)
        return 2
    # Parse every input before writing any output, so a malformed file can
    # never leave a torn half-written tree behind.
    members_doc = json.loads(MEMBERS_JSON.read_text(encoding="utf-8"))
    index_doc = json.loads(INDEX_PAGE_JSON.read_text(encoding="utf-8"))

    data = build_status(members_doc, http_fetch)
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    status = {"generated": today, **data}

    write_json(STATUS_JSON, status)
    write_json(STATUS_PAGE_JSON, render_status_page(status))
    if patch_index(index_doc, status):
        write_json(INDEX_PAGE_JSON, index_doc)
    print(f"wrote {STATUS_JSON} and {STATUS_PAGE_JSON} (generated {status['generated']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
