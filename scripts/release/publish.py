#!/usr/bin/env python3
"""Publish a Concord member mod's jar to Modrinth and CurseForge.

Driven entirely by environment variables set by the reusable release workflow
(.github/workflows/mod-release.yml). Each platform is independent and
self-skips when its token — and, for CurseForge, its project id — is absent.

Modrinth runs first and must succeed before CurseForge is attempted, which
keeps CurseForge the terminal step: a re-run of a partially-failed release
re-attempts only what's left. Modrinth is idempotent by version_number;
CurseForge, being last, only runs when it hasn't already succeeded.

Dependencies come from fabric.mod.json's suggests/recommends (optional), with a
repo-local .github/release-slug-overrides.json remapping any mod id whose
platform slug differs from its Fabric id. They are best-effort: an unresolvable
Modrinth slug is dropped, and a CurseForge upload that fails with relations is
retried once without them, so a stale sibling slug never blocks a release.

The Modrinth version's supported environment defaults to client_and_server (the
suite is client+server mods) and is overridable per mod via the ENVIRONMENT
input for the rare client-only or server-only member.
"""
from __future__ import annotations

import glob
import json
import os
import pathlib
import sys
import time

import requests

MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_API = "https://minecraft.curseforge.com/api"
JAR_CONTENT_TYPE = "application/java-archive"
OK = (200, 201)
TIMEOUT = 120


def log(msg: str) -> None:
    print(msg, flush=True)


def warn(msg: str) -> None:
    print(f"::warning::{msg}", flush=True)


def error(msg: str) -> None:
    print(f"::error::{msg}", flush=True)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def find_jar() -> str:
    explicit = env("JAR")
    if explicit:
        return explicit
    mod_id = env("MOD_ID")
    candidates = [
        f for f in sorted(glob.glob(f"dist/{mod_id}-*.jar"))
        if not f.endswith(("-sources.jar", "-dev.jar"))
    ]
    if not candidates:
        error(f"No distributable jar found in dist/ for {mod_id}")
        sys.exit(1)
    return candidates[0]


def find_fabric_mod_json() -> str | None:
    """Locate the shipped manifest, which is the only one carrying release metadata.

    A mod with gametests ships a second manifest at src/gametest/resources for its
    separate <modid>-gametest mod. That one declares no suggests/recommends, and
    "src/gametest" sorts ahead of "src/main", so a naive first-match would silently
    publish with no optional dependencies at all.
    """
    explicit = env("FABRIC_MOD_JSON")
    if explicit and os.path.isfile(explicit):
        return explicit
    canonical = os.path.join("src", "main", "resources", "fabric.mod.json")
    if os.path.isfile(canonical):
        return canonical
    matches = [
        m for m in sorted(glob.glob("**/resources/fabric.mod.json", recursive=True))
        if "gametest" not in pathlib.PurePath(m).parts
    ]
    return matches[0] if matches else None


def load_dependencies() -> list[dict]:
    """suggests + recommends from fabric.mod.json as optional deps, with slug
    overrides applied. Returns dicts of {id, modrinth, curseforge, type}."""
    path = find_fabric_mod_json()
    if not path:
        log("No fabric.mod.json found; no release dependencies")
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            meta = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        warn(f"Could not parse {path} ({exc}); no release dependencies")
        return []

    overrides: dict = {}
    overrides_path = env("OVERRIDES_FILE") or ".github/release-slug-overrides.json"
    if os.path.isfile(overrides_path):
        try:
            with open(overrides_path, encoding="utf-8") as handle:
                overrides = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            warn(f"Ignoring unparseable {overrides_path} ({exc})")

    ids = sorted(set(meta.get("suggests") or {}) | set(meta.get("recommends") or {}))
    deps = []
    for dep_id in ids:
        override = overrides.get(dep_id, {})
        deps.append({
            "id": dep_id,
            "modrinth": override.get("modrinth", dep_id),
            "curseforge": override.get("curseforge", dep_id),
            "type": "optional",
        })
    if deps:
        log(f"Optional dependencies: {[d['id'] for d in deps]}")
    return deps


def request_with_retries(method: str, url: str, *, attempts: int = 3, **kwargs):
    """Issue a request, retrying only transient failures (transport error or
    5xx). 2xx and 4xx return immediately so the caller can react (e.g. drop
    CurseForge relations on a 400). Returns the final Response, or None if every
    attempt hit a transport error."""
    response = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.request(method, url, timeout=TIMEOUT, **kwargs)
        except requests.RequestException as exc:
            warn(f"{method} {url} errored ({exc}); attempt {attempt}/{attempts}")
            response = None
        else:
            if response.status_code in OK or response.status_code < 500:
                return response
            warn(f"{method} {url} -> HTTP {response.status_code}; "
                 f"attempt {attempt}/{attempts}: {response.text[:300]}")
        if attempt < attempts:
            time.sleep(10)
    return response


def read_jar(jar: str) -> bytes:
    with open(jar, "rb") as handle:
        return handle.read()


# ---------------------------------------------------------------- Modrinth ---

def modrinth_publish(jar: str, changelog: str, deps: list[dict]) -> bool:
    token = env("MODRINTH_TOKEN")
    if not token:
        log("No MODRINTH_TOKEN; skipping Modrinth publish")
        return True
    project = env("MODRINTH_ID")
    version = env("VERSION")
    headers = {"Authorization": token}

    # Idempotency: skip if this version_number already exists on the project.
    existing = requests.get(f"{MODRINTH_API}/project/{project}/version",
                            headers=headers, timeout=TIMEOUT)
    if existing.ok and any(v.get("version_number") == version for v in existing.json()):
        log(f"Modrinth already has {project} {version}; skipping")
        return True

    # Modrinth dependencies are by project_id, so resolve each slug (public).
    dependencies = []
    for dep in deps:
        slug = dep["modrinth"]
        resp = requests.get(f"{MODRINTH_API}/project/{slug}", timeout=TIMEOUT)
        if resp.ok and resp.json().get("id"):
            dependencies.append({
                "project_id": resp.json()["id"],
                "dependency_type": dep["type"],
            })
        else:
            warn(f"Modrinth dependency '{slug}' did not resolve; skipping")

    prerelease = env("PRERELEASE") == "true"
    data = {
        "name": env("TITLE"),
        "version_number": version,
        "changelog": changelog,
        "dependencies": dependencies,
        "game_versions": csv(env("GAME_VERSIONS")),
        "version_type": "beta" if prerelease else "release",
        "environment": env("ENVIRONMENT") or "client_and_server",
        "loaders": [loader.lower() for loader in csv(env("LOADERS"))],
        "featured": not prerelease,
        "project_id": project,
        "file_parts": ["file"],
        "primary_file": "file",
    }
    files = {
        "data": (None, json.dumps(data), "application/json"),
        "file": (os.path.basename(jar), read_jar(jar), JAR_CONTENT_TYPE),
    }
    log(f"Publishing {jar} to Modrinth project {project}")
    resp = request_with_retries("POST", f"{MODRINTH_API}/version",
                                headers=headers, files=files)
    if not resp or resp.status_code not in OK:
        error(f"Modrinth upload failed (HTTP {getattr(resp, 'status_code', 'n/a')})")
        if resp is not None:
            log(resp.text[:500])
        return False
    log(f"✅ Published to Modrinth ({resp.json().get('id', '?')})")
    return True


# -------------------------------------------------------------- CurseForge ---

def curseforge_resolve_versions(token: str, game_versions: list[str],
                                loaders: list[str]) -> list[int] | None:
    """Resolve game-version and loader names to CurseForge numeric ids within
    the correct version-type category. A name like "1.21.1" exists in several
    categories (the real minecraft-1-21 entry plus bukkit/addon ones the upload
    API rejects), so game versions are matched only under a "minecraft*" type
    and loaders only under "modloader*". Returns None on a catalogue fetch
    failure."""
    headers = {"X-Api-Token": token}
    versions = requests.get(f"{CURSEFORGE_API}/game/versions",
                            headers=headers, timeout=TIMEOUT)
    types = requests.get(f"{CURSEFORGE_API}/game/version-types",
                         headers=headers, timeout=TIMEOUT)
    if not (versions.ok and types.ok):
        return None

    slug_by_type = {t["id"]: t["slug"] for t in types.json()}
    want_versions = {name.lower() for name in game_versions}
    want_loaders = {name.lower() for name in loaders}
    ids = set()
    for version in versions.json():
        slug = slug_by_type.get(version["gameVersionTypeID"], "")
        name = version["name"].lower()
        if slug.startswith("minecraft") and name in want_versions:
            ids.add(version["id"])
        elif slug.startswith("modloader") and name in want_loaders:
            ids.add(version["id"])
    return sorted(ids)


def curseforge_publish(jar: str, changelog: str, deps: list[dict]) -> bool:
    token = env("CURSEFORGE_TOKEN")
    project = env("CURSEFORGE_ID")
    if not token or not project:
        log("No CURSEFORGE_TOKEN or curseforge-id; skipping CurseForge publish")
        return True

    game_versions = csv(env("GAME_VERSIONS"))
    loaders = csv(env("LOADERS"))
    version_ids = curseforge_resolve_versions(token, game_versions, loaders)
    if version_ids is None:
        error("Could not fetch the CurseForge game-version catalogues")
        return False
    if not version_ids:
        error(f"Could not resolve any CurseForge version ids for "
              f"{env('GAME_VERSIONS')} / {env('LOADERS')}")
        return False
    log(f"Resolved CurseForge version ids: {version_ids}")

    relations = [
        {"slug": dep["curseforge"],
         "type": "requiredDependency" if dep["type"] == "required"
                 else "optionalDependency"}
        for dep in deps
    ]
    prerelease = env("PRERELEASE") == "true"
    jar_bytes = read_jar(jar)
    url = f"{CURSEFORGE_API}/projects/{project}/upload-file"

    def attempt(include_relations: bool):
        metadata = {
            "changelog": changelog,
            "changelogType": "markdown",
            "displayName": env("TITLE"),
            "gameVersions": version_ids,
            "releaseType": "beta" if prerelease else "release",
        }
        if include_relations and relations:
            metadata["relations"] = {"projects": relations}
        # metadata is a plain multipart text field, not a JSON body part:
        # CurseForge binds it by field name and only then reads changelogType.
        # Tagging the part application/json leaves it unbound, so CurseForge
        # falls back to its changelogType=text default and renders the markdown
        # changelog as escaped, newline-collapsed plain text.
        data = {"metadata": json.dumps(metadata)}
        files = {
            "file": (os.path.basename(jar), jar_bytes, JAR_CONTENT_TYPE),
        }
        return request_with_retries("POST", url, headers={"X-Api-Token": token},
                                    data=data, files=files)

    log(f"Publishing {jar} to CurseForge project {project}")
    if relations:
        log(f"CurseForge dependencies: {[r['slug'] for r in relations]}")
    resp = attempt(include_relations=True)
    if (not resp or resp.status_code not in OK) and relations:
        warn("CurseForge upload failed; retrying once without optional dependencies")
        if resp is not None:
            log(resp.text[:500])
        resp = attempt(include_relations=False)
    if not resp or resp.status_code not in OK:
        error(f"CurseForge upload failed (HTTP {getattr(resp, 'status_code', 'n/a')})")
        if resp is not None:
            log(resp.text[:500])
        return False
    log(f"✅ Published to CurseForge ({resp.json().get('id', '?')})")
    return True


def main() -> None:
    jar = find_jar()
    changelog_file = env("CHANGELOG_FILE") or "/tmp/release-body.md"
    changelog = ""
    if os.path.isfile(changelog_file):
        with open(changelog_file, encoding="utf-8") as handle:
            changelog = handle.read()
    deps = load_dependencies()

    # Modrinth first and must succeed before CurseForge runs (see module
    # docstring): that ordering keeps CurseForge the terminal, re-run-safe step.
    if not modrinth_publish(jar, changelog, deps):
        sys.exit(1)
    if not curseforge_publish(jar, changelog, deps):
        sys.exit(1)


if __name__ == "__main__":
    main()
