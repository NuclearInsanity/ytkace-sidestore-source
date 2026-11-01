#!/usr/bin/env python3
"""Publish an AltStore/SideStore feed linking ONLY to official YTKACE release IPAs.

Requires Python 3.11+, stdlib only. The action fetches release metadata on every
run, but downloads the IPA to inspect its Info.plist only for a new release.
"""

from __future__ import annotations

import json
import os
import pathlib
import plistlib
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone

UPSTREAM = "itzzace/ytkace"
RELEASES_API = f"https://api.github.com/repos/{UPSTREAM}/releases?per_page=40"
RELEASE_ASSET_RE = re.compile(
    r"^YTKACE_\d+(?:\.\d+)+_YouTube_\d+(?:\.\d+)+\.ipa$", re.IGNORECASE
)
SOURCE_PATH = pathlib.Path(__file__).resolve().parent.parent / "source.json"
ICON_URL = "https://avatars.githubusercontent.com/u/318309682?v=4"


def fetch_json(url: str) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "official-ytkace-sidestore-source/1.0"}
    if token := os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.load(response)


def find_latest_asset(releases: list[dict]) -> tuple[dict, dict]:
    for release in sorted(releases, key=lambda r: r.get("published_at") or "", reverse=True):
        if release.get("draft") or release.get("prerelease"):
            continue
        for asset in release.get("assets", []):
            url = asset.get("browser_download_url", "")
            parsed = urllib.parse.urlparse(url)
            if (
                parsed.scheme == "https"
                and parsed.hostname == "github.com"
                and parsed.path.lower().startswith("/itzzace/ytkace/releases/download/")
                and RELEASE_ASSET_RE.fullmatch(asset.get("name", ""))
                and asset.get("size", 0) > 0
            ):
                return release, asset
    raise RuntimeError("No official iOS 17+ YTKACE IPA asset found in recent stable releases; feed left unchanged.")


def read_ipa_metadata(download_url: str) -> dict:
    # The download is an official release binary, not a third-party repackage.
    request = urllib.request.Request(download_url, headers={"User-Agent": "ytkace-sidestore-source/1.0"})
    with tempfile.TemporaryDirectory(prefix="ytkace_") as temp:
        ipa = pathlib.Path(temp) / "YTKACE.ipa"
        with urllib.request.urlopen(request, timeout=180) as response, ipa.open("wb") as target:
            shutil.copyfileobj(response, target)
        with zipfile.ZipFile(ipa) as archive:
            candidates = [n for n in archive.namelist() if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", n)]
            if len(candidates) != 1:
                raise RuntimeError(f"Expected one root app Info.plist, found {len(candidates)}")
            plist = plistlib.loads(archive.read(candidates[0]))
    result = {key: str(plist.get(key, "")).strip() for key in (
        "CFBundleIdentifier", "CFBundleShortVersionString", "CFBundleVersion", "MinimumOSVersion"
    )}
    if not all(result[k] for k in ("CFBundleIdentifier", "CFBundleShortVersionString", "CFBundleVersion")):
        raise RuntimeError("IPA missing required Info.plist version/bundle fields")
    return result


def safe_description(release: dict) -> str:
    notes = release.get("body", "") or ""
    notes = notes.strip()[:7000]
    return f"Official YTKACE release {release.get('tag_name', '')}.\n\n{notes}"


def make_source(previous: dict, release: dict, asset: dict, metadata: dict, owner_repo: str) -> dict:
    source_url = f"https://raw.githubusercontent.com/{owner_repo}/main/source.json"
    published = (release.get("published_at") or datetime.now(timezone.utc).isoformat())[:10]
    version = metadata["CFBundleShortVersionString"]
    minimum_os = metadata.get("MinimumOSVersion") or "17.0"
    # Do not label the regular IPA as compatible with iOS 16.
    def parts(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)
    if parts(minimum_os) < parts("17.0"):
        minimum_os = "17.0"
    entry = {
        "version": version,
        "buildVersion": metadata["CFBundleVersion"],
        "date": published,
        "localizedDescription": safe_description(release),
        "downloadURL": asset["browser_download_url"],
        "size": asset["size"],
        "minOSVersion": minimum_os,
    }
    old_versions = (previous.get("apps") or [{}])[0].get("versions", [])
    versions = [entry] + [v for v in old_versions if v.get("downloadURL") != entry["downloadURL"]]
    versions = versions[:15]
    return {
        "name": "YTKACE — Official Releases",
        "identifier": f"com.{owner_repo.split('/')[0].lower()}.ytkace.official",
        "apiVersion": "v2",
        "subtitle": "Unmodified IPA releases from itzzace/ytkace",
        "description": "Direct official GitHub release IPAs. This source tracks the original developer's builds; no repackaging or injected extras.",
        "iconURL": ICON_URL,
        "website": "https://github.com/itzzace/ytkace",
        "sourceURL": source_url,
        "apps": [{
            "name": "YTKACE",
            "bundleIdentifier": metadata["CFBundleIdentifier"],
            "developerName": "itzzace0",
            "subtitle": f"Official {release.get('tag_name', 'release')} • YouTube {version}",
            "category": "photo-video",
            "localizedDescription": "YTKACE adds SponsorBlock, background playback, downloads and playback controls to YouTube.",
            "iconURL": ICON_URL,
            "tintColor": "FF0033",
            # Legacy fields kept for compatibility with some source readers.
            "version": version,
            "versionDate": published,
            "versionDescription": safe_description(release),
            "downloadURL": asset["browser_download_url"],
            "size": asset["size"],
            "versions": versions,
        }],
        "news": [],
    }


def main() -> None:
    owner_repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", owner_repo):
        raise SystemExit("GITHUB_REPOSITORY must be set to owner/repo (set automatically by GitHub Actions)")
    previous = json.loads(SOURCE_PATH.read_text()) if SOURCE_PATH.exists() else {}
    releases = fetch_json(RELEASES_API)
    if not isinstance(releases, list):
        raise RuntimeError("Unexpected GitHub API response; source left unchanged")
    release, asset = find_latest_asset(releases)
    newest = (previous.get("apps") or [{}])[0]
    if newest.get("downloadURL") == asset["browser_download_url"]:
        print(f"No new release: {release.get('tag_name')}")
        return
    print(f"Reading metadata from official release {release.get('tag_name')}: {asset['name']}")
    metadata = read_ipa_metadata(asset["browser_download_url"])
    source = make_source(previous, release, asset, metadata, owner_repo)
    SOURCE_PATH.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {SOURCE_PATH}: {release.get('tag_name')}, app version {metadata['CFBundleShortVersionString']}")


if __name__ == "__main__":
    main()
