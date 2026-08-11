import os
import re
import sys
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "haxelib.json"
OUT_PATH = ROOT / "package" / "haxelib.json"


HAXELIB_LICENSE_MAP = {
    "MIT": "MIT",
    "Apache-2.0": "Apache",
    "BSD-2-Clause": "BSD",
    "BSD-3-Clause": "BSD",
    "GPL-2.0": "GPL",
    "GPL-3.0": "GPL",
    "LGPL-2.1": "LGPL",
    "LGPL-3.0": "LGPL",
    "MPL-2.0": "MPL",
    "Unlicense": "Public",
    "CC0-1.0": "Public",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def read_json_file(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        fail(f"{Path(path).name} must contain a JSON object")

    return data


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}

    return read_json_file(CONFIG_PATH)


def github_api_get(path: str):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if not token:
        fail("GITHUB_TOKEN is missing")
    if not repo:
        fail("GITHUB_REPOSITORY is missing")

    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def github_api_get_absolute(url: str):
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        fail("GITHUB_TOKEN is missing")

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def get_release_payload() -> dict:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        fail("GITHUB_EVENT_PATH is missing")

    event = read_json_file(event_path)
    release = event.get("release")

    if not isinstance(release, dict):
        fail("This workflow must be triggered by a GitHub Release event")

    return release


def normalize_version(tag_name: str) -> str:
    version = tag_name.strip()

    if version.startswith("v"):
        version = version[1:]

    if not re.match(r"^\d+\.\d+\.\d+([.-][A-Za-z0-9.-]+)?$", version):
        fail(
            f"Invalid version from release tag: {tag_name!r}. "
            "Use tags like v0.1.0, v1.2.3, v1.0.0-beta.1."
        )

    return version


def normalize_name(name: str) -> str:
    name = str(name).strip()

    if not name:
        fail("Package name is empty")

    if not re.match(r"^[A-Za-z0-9_.-]+$", name):
        fail(
            f"Invalid package name: {name!r}. "
            "Use only letters, numbers, underscore, dot or hyphen."
        )

    return name


def normalize_tags(tags) -> list[str]:
    if tags is None:
        return []

    if not isinstance(tags, list):
        fail("tags must be a JSON array or GitHub topics array")

    result = []
    for tag in tags:
        value = str(tag).strip()
        if value:
            result.append(value)

    return result


def normalize_contributors(contributors) -> list[str]:
    if contributors is None:
        return []

    if not isinstance(contributors, list):
        fail("contributors must be a JSON array")

    result = []
    for contributor in contributors:
        value = str(contributor).strip()
        if value:
            result.append(value)

    return result


def normalize_dependencies(dependencies) -> dict:
    if dependencies is None:
        return {}

    if isinstance(dependencies, list):
        if len(dependencies) == 0:
            return {}
        fail("dependencies must be a JSON object; use {} for no dependencies")

    if not isinstance(dependencies, dict):
        fail("dependencies must be a JSON object")

    return {
        str(name): "" if version is None else str(version)
        for name, version in dependencies.items()
    }


def get_github_contributors() -> list[str]:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        fail("GITHUB_REPOSITORY is missing")

    per_page = 100
    page = 1
    result = []
    seen = set()

    while True:
        path = f"/contributors?per_page={per_page}&page={page}"
        data = github_api_get(path)

        if not isinstance(data, list):
            fail("Unexpected GitHub contributors response")

        if not data:
            break

        for contributor in data:
            if not isinstance(contributor, dict):
                continue

            login = str(contributor.get("login") or "").strip()
            if not login or login in seen:
                continue

            seen.add(login)

            contributor_url = str(contributor.get("url") or "").strip()
            profile_name = ""

            if contributor_url:
                profile = github_api_get_absolute(contributor_url)
                if isinstance(profile, dict):
                    profile_name = str(profile.get("name") or "").strip()

            result.append(profile_name or login)

        if len(data) < per_page:
            break

        page += 1

    return result


def main() -> None:
    config = load_config()
    release = get_release_payload()

    repo_data = github_api_get("")
    topics_data = github_api_get("/topics")

    repo_name = repo_data.get("name") or ""
    repo_url = repo_data.get("html_url") or ""
    repo_description = repo_data.get("description") or ""
    repo_topics = topics_data.get("names") or []

    release_tag = release.get("tag_name") or ""
    release_title = str(release.get("name") or "").strip()
    release_body = release.get("body") or ""
    release_note = release_body.strip() or release_title or "New release"

    license_info = repo_data.get("license") or {}
    spdx_license = license_info.get("spdx_id")

    haxelib_license = config.get("license")
    if not haxelib_license:
        haxelib_license = HAXELIB_LICENSE_MAP.get(spdx_license)

    if not haxelib_license:
        fail(
            f"Cannot map GitHub license {spdx_license!r} to haxelib license. "
            "Set license explicitly in haxelib.json."
        )

    contributors = normalize_contributors(config.get("contributors"))
    if not contributors:
        contributors = get_github_contributors()

    generated_package = {
        "name": normalize_name(config.get("name") or repo_name),
        "url": str(config.get("url") or repo_url),
        "license": str(haxelib_license),
        "tags": normalize_tags(config.get("tags", repo_topics)),
        "description": str(config.get("description") or repo_description),
        "version": str(config.get("version") or normalize_version(release_tag)),
        "classPath": str(config.get("classPath", "src")),
        "releasenote": str(config.get("releasenote") or release_note),
        "contributors": contributors,
    }

    package = dict(generated_package)
    package.update(config)

    package["name"] = normalize_name(package.get("name") or repo_name)
    package["url"] = str(package.get("url") or repo_url)
    package["license"] = str(package.get("license") or haxelib_license)
    package["tags"] = normalize_tags(package.get("tags", repo_topics))
    package["description"] = str(package.get("description") or repo_description)
    package["version"] = str(package.get("version") or normalize_version(release_tag))
    package["classPath"] = str(package.get("classPath", "src"))
    package["releasenote"] = str(package.get("releasenote") or release_note)
    package["contributors"] = normalize_contributors(package.get("contributors"))

    if not package["description"]:
        fail("Description is empty. Add GitHub repo description or description in haxelib.json.")

    if not package["contributors"]:
        fail("contributors is required. Add contributors to haxelib.json.")

    package["dependencies"] = normalize_dependencies(package.get("dependencies"))

    if "main" in package and package["main"] is not None:
        package["main"] = str(package["main"])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Generated {OUT_PATH}")
    print(json.dumps(package, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
