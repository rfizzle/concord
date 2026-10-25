#!/usr/bin/env python3
"""Rewrite the dependencies of already-published Modrinth versions.

For each version, recompute what publish.py's load_dependencies would produce
for that member at that release tag (fabric.mod.json read from the member repo
at v<version_number>, slugs from the hub's members.json) and PATCH
/v2/version/{id} when it differs. Dry-run by default: prints the before/after
diff per version and writes nothing. `--apply` PATCHes; it needs MODRINTH_TOKEN
in the environment.

    fix-modrinth-deps.py VERSION_ID [VERSION_ID ...]
    fix-modrinth-deps.py --member prosperity 1.1.0 1.1.0-beta.2   # by version number

The member repo is read from $PROJECTS_DIR/<member> (default ~/Projects).
Every resolved project goes through the same impostor guard as publish.py; a
version whose dependencies cannot be rebuilt cleanly is reported and skipped.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import requests

HERE = pathlib.Path(__file__).resolve().parent
HUB = HERE.parent.parent
API = "https://api.modrinth.com/v2"
TIMEOUT = 60

_spec = importlib.util.spec_from_file_location("publish", HERE / "publish.py")
publish = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(publish)


def get(path: str):
    resp = requests.get(f"{API}{path}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def git_show(repo: pathlib.Path, tag: str, path: str) -> str | None:
    result = subprocess.run(["git", "-C", str(repo), "show", f"{tag}:{path}"],
                            capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def project_label(cache: dict, project_id: str) -> str:
    if project_id not in cache:
        try:
            p = get(f"/project/{project_id}")
            cache[project_id] = f"{p.get('slug')} ({project_id})"
        except requests.RequestException:
            cache[project_id] = project_id
    return cache[project_id]


def rebuild(repo: pathlib.Path, tag: str, members_file: pathlib.Path) -> list[dict]:
    """Dependencies as publish.py would build them for `repo` at `tag`. Raises
    RuntimeError if the manifest is missing or a dependency cannot be vouched
    for."""
    manifest = git_show(repo, tag, "src/main/resources/fabric.mod.json")
    if manifest is None:
        raise RuntimeError(f"no src/main/resources/fabric.mod.json at {tag}")
    overrides = git_show(repo, tag, ".github/release-slug-overrides.json")
    prev = os.getcwd()
    saved = {k: os.environ.get(k) for k in ("MEMBERS_FILE", "OVERRIDES_FILE", "FABRIC_MOD_JSON")}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        manifest_path = root / "fabric.mod.json"
        manifest_path.write_text(manifest, encoding="utf-8")
        os.environ["MEMBERS_FILE"] = str(members_file)
        os.environ["FABRIC_MOD_JSON"] = str(manifest_path)
        os.environ["OVERRIDES_FILE"] = str(root / "none.json")
        if overrides:
            (root / "overrides.json").write_text(overrides, encoding="utf-8")
            os.environ["OVERRIDES_FILE"] = str(root / "overrides.json")
        os.chdir(root)
        try:
            deps = publish.load_dependencies()
        finally:
            os.chdir(prev)
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    out = []
    for dep in deps:
        slug = dep["modrinth"]
        if slug is None:
            continue
        try:
            project = get(f"/project/{slug}")
        except requests.RequestException as exc:
            if dep["type"] == "required":
                raise RuntimeError(f"required dependency '{slug}' did not resolve ({exc})")
            print(f"  skip optional '{slug}': did not resolve")
            continue
        if not publish.modrinth_project_trusted(dep, project):
            raise RuntimeError(f"'{dep['id']}' resolved '{slug}' to {project.get('id')} "
                               f"({project.get('title')!r}): not the sibling or a mapped slug")
        out.append({"project_id": project["id"], "dependency_type": dep["type"]})
    return out


def keyset(deps: list[dict]) -> set:
    return {(d.get("project_id"), d.get("dependency_type")) for d in deps}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("versions", nargs="+", help="Modrinth version ids (or version numbers with --member)")
    parser.add_argument("--member", help="member id; treat the arguments as version numbers of its project")
    parser.add_argument("--apply", action="store_true", help="PATCH the versions (default: dry run)")
    args = parser.parse_args()

    members_file = HUB / "members.json"
    registry = json.loads(members_file.read_text(encoding="utf-8"))
    by_project = {(m.get("store", {}).get("modrinth") or {}).get("id"): m["id"]
                  for m in registry["members"]}
    projects_dir = pathlib.Path(os.environ.get("PROJECTS_DIR") or pathlib.Path.home() / "Projects")
    token = os.environ.get("MODRINTH_TOKEN", "")
    if args.apply and not token:
        print("--apply needs MODRINTH_TOKEN in the environment", file=sys.stderr)
        return 2

    ids = list(args.versions)
    if args.member:
        member = next((m for m in registry["members"] if m["id"] == args.member), None)
        if not member:
            print(f"unknown member {args.member}", file=sys.stderr)
            return 2
        listing = get(f"/project/{member['store']['modrinth']['id']}/version")
        numbers = {v["version_number"]: v["id"] for v in listing}
        missing = [n for n in ids if n not in numbers]
        if missing:
            print(f"no such version(s) on Modrinth: {missing}", file=sys.stderr)
            return 2
        ids = [numbers[n] for n in ids]

    labels: dict = {}
    failed = 0
    for vid in ids:
        version = get(f"/version/{vid}")
        member_id = by_project.get(version["project_id"])
        number = version["version_number"]
        print(f"== {member_id or version['project_id']} {number} ({vid})")
        if not member_id:
            print("  project is not a Concord member; skipped")
            failed += 1
            continue
        try:
            after = rebuild(projects_dir / member_id, f"v{number}", members_file)
        except RuntimeError as exc:
            print(f"  cannot rebuild: {exc}")
            failed += 1
            continue
        before = version.get("dependencies") or []
        # Only project dependencies are managed; keep any version-pinned or
        # file-named entries a human added by hand.
        kept = [d for d in before if not d.get("project_id")]
        payload = after + kept
        old, new = keyset(before), keyset(payload)
        for key in sorted(old - new, key=str):
            print(f"  - {project_label(labels, key[0])} [{key[1]}]")
        for key in sorted(new - old, key=str):
            print(f"  + {project_label(labels, key[0])} [{key[1]}]")
        if old == new:
            print("  already correct")
            continue
        if not args.apply:
            print("  (dry run; pass --apply to PATCH)")
            continue
        resp = requests.patch(f"{API}/version/{vid}", headers={"Authorization": token},
                              json={"dependencies": payload}, timeout=TIMEOUT)
        if resp.status_code in (200, 204):
            print("  patched")
        else:
            print(f"  PATCH failed: HTTP {resp.status_code} {resp.text[:300]}")
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
