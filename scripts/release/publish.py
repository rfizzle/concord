#!/usr/bin/env python3
"""Publish a Concord member mod's jar to Modrinth and CurseForge.

Driven entirely by environment variables set by the reusable release workflow
(.github/workflows/mod-release.yml). Each platform is independent and
self-skips when its token — and, for CurseForge, its project id — is absent.

Modrinth runs first and must succeed before CurseForge is attempted, which
keeps CurseForge the terminal step: a re-run of a partially-failed release
re-attempts only what's left. Modrinth is idempotent by version_number or jar sha1 and fails closed if it
cannot tell; CurseForge, being last, skips an upload whose display name is
already listed on the project.

Dependencies come from fabric.mod.json: `depends` (minus the platform entries
minecraft, fabricloader, java and fabric) are required, `suggests`/`recommends`
are optional. Mod ids map to store slugs through the hub's members.json (member
and third-party slugs) plus an optional repo-local
.github/release-slug-overrides.json remapping any mod id whose platform slug
differs from its Fabric id; a third-party slug of null means the mod is not on
that store and the relation is skipped without a warning. Optional relations are
best-effort and removed as surgically as CurseForge lets us: an unresolvable
Modrinth slug is dropped, and a CurseForge rejection carrying errorCode 1018
names the offending slug, so only that relation is dropped before retrying.
Only if the upload still fails does it fall back to publishing with no relations
at all — a stale sibling slug never blocks a release, and never costs the
relations that were fine. A required Modrinth dependency that does not resolve
fails the publish, as does any resolved project that is neither the registered
Concord sibling nor a mapped third-party slug: a bare mod id can name an
unrelated project (`tribulation` is not Tribulation) and must not ship as a
relation.

The supported environment defaults to client_and_server (the suite is
client+server mods) and is overridable per mod via the ENVIRONMENT input for the
rare client-only or server-only member. It sets the Modrinth version's
environment and selects the Client/Server ids CurseForge requires on every
upload.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pathlib
import re
import sys
import time

import requests

MODRINTH_API = "https://api.modrinth.com/v2"
CURSEFORGE_API = "https://minecraft.curseforge.com/api"
JAR_CONTENT_TYPE = "application/java-archive"
OK = (200, 201)
TIMEOUT = 120

# CurseForge upload-API error codes we can react to rather than just retry.
# 1018 names the offending slug in its message, which lets us drop that one
# relation instead of discarding the whole list (the approach Kira-NT/mc-publish
# takes in curseforge-error.ts).
CF_INVALID_PROJECT_SLUG = 1018
CF_INVALID_GAME_VERSION_ID = 1009
CF_INVALID_SLUG_RE = re.compile(r"Invalid slug in project relations: '([^']*)'")

# Backoff for transient (5xx / transport) failures. CurseForge served four 500s
# out of five uploads on 2026-08-29 and the release landed on the last attempt
# the old flat 3x10s budget allowed, so the delay grows and the budget is wider.
RETRY_ATTEMPTS = 4
RETRY_BASE_DELAY = 10
RETRY_MAX_DELAY = 80

# Platform entries in fabric.mod.json `depends` that are not mods to relate to.
PLATFORM_DEPENDS = {"minecraft", "fabricloader", "java", "fabric"}
CFWIDGET_API = "https://api.cfwidget.com"


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
    """depends (required) + suggests/recommends (optional) from fabric.mod.json,
    with slug overrides applied. Returns dicts of {id, modrinth, curseforge,
    type, trust, guarded}. A store slug of None means the mod is not on that
    store. `trust` says how the Modrinth slug is vouched for, for the impostor
    guard: ("id", project_id) for a sibling, ("slug", slug) for a mapped slug,
    or None for an id the registry does not map; `guarded` is False when no
    registry was loaded at all."""
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

    siblings, third_party = load_hub_slugs()
    registry_loaded = bool(siblings or third_party)

    required = {d for d in (meta.get("depends") or {}) if d not in PLATFORM_DEPENDS}
    required.discard(meta.get("id"))
    optional = set(meta.get("suggests") or {}) | set(meta.get("recommends") or {})
    optional.discard(meta.get("id"))
    deps = []
    for dep_id in sorted(required | optional):
        # Precedence: an explicit repo-local override wins, then the hub registry
        # (members first, then the third-party map), then the bare mod id.
        override = overrides.get(dep_id, {})
        hub = siblings.get(dep_id) or third_party.get(dep_id, {})
        slugs = {}
        for platform in ("modrinth", "curseforge"):
            if platform in override:
                slugs[platform] = override[platform]
            elif platform in hub:
                slugs[platform] = hub[platform]
            else:
                slugs[platform] = dep_id
        trust = None
        if "modrinth" in override:
            trust = ("slug", override["modrinth"])
        elif dep_id in siblings and siblings[dep_id].get("modrinth_id"):
            trust = ("id", siblings[dep_id]["modrinth_id"])
        elif "modrinth" in hub:
            trust = ("slug", hub["modrinth"])
        deps.append({
            "id": dep_id,
            "modrinth": slugs["modrinth"],
            "curseforge": slugs["curseforge"],
            "type": "required" if dep_id in required else "optional",
            "trust": trust,
            "guarded": registry_loaded,
        })
    if deps:
        log(f"Required dependencies: {[d['id'] for d in deps if d['type'] == 'required']}")
        log(f"Optional dependencies: {[d['id'] for d in deps if d['type'] == 'optional']}")
        remapped = [f"{d['id']}->{d['modrinth']}" for d in deps if d["modrinth"] != d["id"]]
        if remapped:
            log(f"Resolved store slugs: {remapped}")
    return deps


def load_hub_slugs() -> tuple[dict[str, dict], dict[str, dict]]:
    """Read the hub's slug registries: (member slugs, third-party slugs).

    A member names its siblings in fabric.mod.json's `suggests` by **mod id**
    (`tribulation`), but both stores list them under a longer slug
    (`tribulation-difficulty-overhaul`). Left unmapped, Modrinth reports the
    relation as unresolvable and drops it, so a sibling integration is silently
    missing from the published listing.

    The same mismatch hits non-Concord mods: `roughlyenoughitems` lists as `rei`
    on Modrinth and `roughly-enough-items` on CurseForge. Those live under
    members.json's `thirdPartySlugs`, because the per-repo override file drifts —
    five members carried an identical copy of it and cultivation, the sixth to
    declare REI, had none, so its v1.0.0-beta.1 published without the relation.

    A third-party entry may name a store as null: the mod is not listed there, and
the relation is skipped on that store without a warning.

members.json is the canonical registry of both, so read it rather than
    restating them in eight repo-local override files where they can drift.
    The release workflow checks concord out to `.concord/`; MEMBERS_FILE and the
    sibling-checkout path cover local runs. A missing file is not an error — a
    bare clone just falls back to the mod id, exactly as before.
    """
    for candidate in (env("MEMBERS_FILE"), ".concord/members.json", "../concord/members.json"):
        if not candidate or not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, encoding="utf-8") as handle:
                registry = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            warn(f"Ignoring unparseable {candidate} ({exc})")
            return {}, {}
        slugs = {}
        for member in registry.get("members") or []:
            store = member.get("store") or {}
            entry = {}
            for platform in ("modrinth", "curseforge"):
                slug = (store.get(platform) or {}).get("slug")
                if slug:
                    entry[platform] = slug
            project_id = (store.get("modrinth") or {}).get("id")
            if entry and project_id:
                entry["modrinth_id"] = project_id
            if member.get("id") and entry:
                slugs[member["id"]] = entry
        third_party = {}
        for dep_id, entry in (registry.get("thirdPartySlugs") or {}).items():
            if not isinstance(entry, dict):
                continue
            mapped = {k: v for k, v in entry.items()
                      if k in ("modrinth", "curseforge") and (v is None or v)}
            if mapped:
                third_party[dep_id] = mapped
        log(f"Loaded {len(slugs)} sibling and {len(third_party)} third-party store slugs from {candidate}")
        return slugs, third_party
    return {}, {}


def request_with_retries(method: str, url: str, *,
                         attempts: int = RETRY_ATTEMPTS, **kwargs):
    """Issue a request, retrying only transient failures (transport error or
    5xx) with exponential backoff. 2xx and 4xx return immediately so the caller
    can react to the body — CurseForge reports a bad relation slug as a 4xx
    carrying errorCode 1018, which `curseforge_publish` uses to drop just that
    slug. Returns the final Response, or None if every attempt hit a transport
    error.

    Note a 5xx is *not* evidence about relations: on 2026-08-29 CurseForge
    returned 500 both with and without them. Backoff exists for that case, and
    the relation handling is driven by error codes rather than by exhaustion.
    """
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
            delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
            log(f"  retrying in {delay}s")
            time.sleep(delay)
    return response


def curseforge_error(resp) -> dict | None:
    """Parse a CurseForge upload-API error body, or None if it isn't one."""
    if resp is None:
        return None
    try:
        body = resp.json()
    except ValueError:
        return None
    if isinstance(body, dict) and isinstance(body.get("errorCode"), int):
        return body
    return None


def drop_invalid_slug(relations: list[dict], resp) -> str | None:
    """If `resp` is a 1018 'invalid slug in project relations' error, remove the
    single slug it names from `relations` in place and return it. Returns None
    when the error is something else, or names a slug we are not sending —
    which would otherwise loop forever."""
    body = curseforge_error(resp)
    if not body or body.get("errorCode") != CF_INVALID_PROJECT_SLUG:
        return None
    match = CF_INVALID_SLUG_RE.search(body.get("errorMessage") or "")
    if not match:
        return None
    slug = match.group(1)
    before = len(relations)
    relations[:] = [r for r in relations if r["slug"] != slug]
    return slug if len(relations) != before else None


def read_jar(jar: str) -> bytes:
    with open(jar, "rb") as handle:
        return handle.read()


# ---------------------------------------------------------------- Modrinth ---

def modrinth_has_version(headers: dict, project: str, version: str,
                         sha1: str) -> bool | None:
    """True if the project already has this version_number or a file with this
    sha1; False if it does not; None if the listing could not be read."""
    resp = request_with_retries("GET", f"{MODRINTH_API}/project/{project}/version",
                                headers=headers)
    if resp is None or resp.status_code not in OK:
        return None
    try:
        versions = resp.json()
    except ValueError:
        return None
    for v in versions:
        if v.get("version_number") == version:
            return True
        if any((f.get("hashes") or {}).get("sha1") == sha1 for f in v.get("files") or []):
            return True
    return False


def modrinth_project_trusted(dep: dict, project: dict) -> bool:
    """Impostor guard: a resolved project must be the registered sibling (by
    project id) or the mapped third-party slug. Skipped only when no hub
    registry was loaded, where nothing can be vouched for."""
    if not dep.get("guarded"):
        return True
    trust = dep.get("trust")
    if not trust:
        return False
    kind, value = trust
    if kind == "id":
        return project.get("id") == value
    return value in (project.get("slug"), project.get("id"))


def modrinth_publish(jar: str, changelog: str, deps: list[dict]) -> bool:
    token = env("MODRINTH_TOKEN")
    if not token:
        log("No MODRINTH_TOKEN; skipping Modrinth publish")
        return True
    project = env("MODRINTH_ID")
    version = env("VERSION")
    headers = {"Authorization": token}

    jar_bytes = read_jar(jar)
    sha1 = hashlib.sha1(jar_bytes).hexdigest()

    # Idempotency: skip if this version_number or this exact jar is already on
    # the project. If we cannot tell, fail rather than risk a duplicate.
    exists = modrinth_has_version(headers, project, version, sha1)
    if exists is None:
        error(f"Could not list Modrinth versions for {project}; refusing to publish blind")
        return False
    if exists:
        log(f"Modrinth already has {project} {version}; skipping")
        return True

    # Modrinth dependencies are by project_id, so resolve each slug (public).
    dependencies = []
    for dep in deps:
        slug = dep["modrinth"]
        if slug is None:
            continue
        resp = request_with_retries("GET", f"{MODRINTH_API}/project/{slug}")
        body = resp.json() if resp is not None and resp.status_code in OK else {}
        if not body.get("id"):
            if dep["type"] == "required":
                error(f"Required Modrinth dependency '{slug}' did not resolve")
                return False
            warn(f"Modrinth dependency '{slug}' did not resolve; skipping")
            continue
        if not modrinth_project_trusted(dep, body):
            error(f"Modrinth dependency '{dep['id']}' resolved '{slug}' to "
                  f"{body.get('id')} ({body.get('title')!r}), which is neither the "
                  f"registered Concord sibling nor a mapped third-party slug; "
                  f"add it to members.json thirdPartySlugs")
            return False
        dependencies.append({
            "project_id": body["id"],
            "dependency_type": dep["type"],
        })

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
        "file": (os.path.basename(jar), jar_bytes, JAR_CONTENT_TYPE),
    }
    log(f"Publishing {jar} to Modrinth project {project}")
    # The create POST is not idempotent, so it is never blindly retried: after
    # any failure the version list is re-read, and a version that landed despite
    # the error (a dropped response) counts as success.
    resp = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        resp = request_with_retries("POST", f"{MODRINTH_API}/version",
                                    attempts=1, headers=headers, files=files)
        if resp is not None and resp.status_code in OK:
            log(f"✅ Published to Modrinth ({resp.json().get('id', '?')})")
            return True
        status = getattr(resp, "status_code", "n/a")
        if resp is not None:
            log(resp.text[:500])
        landed = modrinth_has_version(headers, project, version, sha1)
        if landed:
            log(f"Modrinth upload errored (HTTP {status}) but {version} is present; treating as published")
            return True
        if landed is None or (resp is not None and resp.status_code < 500):
            break
        if attempt < RETRY_ATTEMPTS:
            delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
            log(f"  retrying upload in {delay}s")
            time.sleep(delay)
    error(f"Modrinth upload failed (HTTP {getattr(resp, 'status_code', 'n/a')})")
    return False


# -------------------------------------------------------------- CurseForge ---

def curseforge_environment_names(environment: str) -> set[str]:
    """Map the Modrinth-style ENVIRONMENT input to CurseForge's Client/Server
    environment pseudo-versions. CurseForge treats its environment group as
    mandatory (error 1021 otherwise), so the result is never empty: an unknown
    or unset value falls back to both sides, matching the suite default."""
    value = environment.strip().lower()
    client = value not in {"server_only", "dedicated_server_only"}
    server = value != "client_only"
    names = set()
    if client:
        names.add("client")
    if server:
        names.add("server")
    return names or {"client", "server"}


def curseforge_resolve_versions(token: str, game_versions: list[str],
                                loaders: list[str],
                                environment: str) -> list[int] | None:
    """Resolve game-version, loader, and environment names to CurseForge numeric
    ids within the correct version-type category. A name like "1.21.1" exists in
    several categories (the real minecraft-1-21 entry plus bukkit/addon ones the
    upload API rejects), so game versions are matched only under a "minecraft*"
    type, loaders only under "modloader*", and the Client/Server pseudo-versions
    only under "environment*". CurseForge rejects an upload that carries no
    environment id (error 1021), so a resolve that finds none returns [] to block
    the upload. Returns None on a catalogue fetch failure."""
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
    want_env = curseforge_environment_names(environment)
    ids = set()
    env_ids = set()
    for version in versions.json():
        slug = slug_by_type.get(version["gameVersionTypeID"], "")
        name = version["name"].lower()
        if slug.startswith("minecraft") and name in want_versions:
            ids.add(version["id"])
        elif slug.startswith("modloader") and name in want_loaders:
            ids.add(version["id"])
        elif slug.startswith("environment") and name in want_env:
            env_ids.add(version["id"])
    if not env_ids:
        error(f"No CurseForge environment id resolved for ENVIRONMENT="
              f"{environment!r}; the upload would be rejected (error 1021)")
        return []
    return sorted(ids | env_ids)


def curseforge_has_file(project: str, display_name: str, file_name: str) -> bool | None:
    """True if the project already lists a file with this display name (or jar
    name). The upload token cannot list files (the upload API has no read
    endpoint and the core API needs a separate key), so this reads the public
    CFWidget mirror. None if the listing is unavailable."""
    resp = request_with_retries("GET", f"{CFWIDGET_API}/{project}", attempts=2)
    if resp is None or resp.status_code not in OK:
        return None
    try:
        files = resp.json().get("files")
    except (ValueError, AttributeError):
        return None
    if not isinstance(files, list):
        return None
    return any(f.get("display") == display_name or f.get("name") == file_name
               for f in files)


def curseforge_publish(jar: str, changelog: str, deps: list[dict]) -> bool:
    token = env("CURSEFORGE_TOKEN")
    project = env("CURSEFORGE_ID")
    if not token or not project:
        log("No CURSEFORGE_TOKEN or curseforge-id; skipping CurseForge publish")
        return True

    game_versions = csv(env("GAME_VERSIONS"))
    loaders = csv(env("LOADERS"))
    environment = env("ENVIRONMENT")
    version_ids = curseforge_resolve_versions(token, game_versions, loaders,
                                              environment)
    if version_ids is None:
        error("Could not fetch the CurseForge game-version catalogues")
        return False
    if not version_ids:
        error(f"Could not resolve the required CurseForge version ids for "
              f"{env('GAME_VERSIONS')} / {env('LOADERS')} / {environment}")
        return False
    log(f"Resolved CurseForge version ids: {version_ids}")

    listed = curseforge_has_file(project, env("TITLE"), os.path.basename(jar))
    if listed:
        log(f"CurseForge already has {env('TITLE')!r} on project {project}; skipping")
        return True
    if listed is None:
        warn(f"Could not list CurseForge files for project {project}; the "
             f"duplicate check is skipped and a re-run may upload twice")

    relations = [
        {"slug": dep["curseforge"],
         "type": "requiredDependency" if dep["type"] == "required"
                 else "optionalDependency"}
        for dep in deps
        if dep["curseforge"] is not None
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

    # Peel off bad relations one at a time while CurseForge keeps naming them,
    # so one stale sibling slug costs that slug and not the whole dependency
    # list. Bounded by the relation count: every pass removes exactly one.
    resp = attempt(include_relations=True)
    for _ in range(len(relations)):
        if resp is not None and resp.status_code in OK:
            break
        dropped = drop_invalid_slug(relations, resp)
        if not dropped:
            break
        warn(f"CurseForge rejected the relation '{dropped}'; retrying without it")
        resp = attempt(include_relations=True)

    # Last resort: something about the relations block is wrong in a way
    # CurseForge did not attribute to a named slug. Publishing without the
    # optional dependencies beats failing the release.
    if (not resp or resp.status_code not in OK) and relations:
        warn("CurseForge upload still failing; retrying once without optional dependencies")
        if resp is not None:
            log(resp.text[:500])
        resp = attempt(include_relations=False)

    if not resp or resp.status_code not in OK:
        error(f"CurseForge upload failed (HTTP {getattr(resp, 'status_code', 'n/a')})")
        if resp is not None:
            log(resp.text[:500])
        return False
    if relations:
        log(f"CurseForge relations published: {[r['slug'] for r in relations]}")
    else:
        warn("CurseForge file published with no dependency relations")
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
