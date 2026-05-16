from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass

from .build_info import BUILD_DATE, BUILD_SHA
from .version import APP_RELEASE_VERSION, APP_VERSION


REPO = "jiashusu/valorant-highlight-clipper"
BRANCH = "main"
REPO_URL = f"https://github.com/{REPO}"
DOWNLOAD_URL = f"{REPO_URL}/releases/latest"


@dataclass
class UpdateResult:
    current_sha: str
    remote_sha: str | None
    update_available: bool
    message: str
    download_url: str = DOWNLOAD_URL

    @property
    def current_short(self) -> str:
        return short_sha(self.current_sha)

    @property
    def remote_short(self) -> str:
        return short_sha(self.remote_sha or "")


def short_sha(value: str) -> str:
    if not value or value == "unknown":
        return "unknown"
    return value.strip().lower()[:7]


def shas_match(current_sha: str, remote_sha: str | None) -> bool:
    current = (current_sha or "").strip().lower()
    remote = (remote_sha or "").strip().lower()
    if not current or not remote or current == "unknown":
        return False
    return current.startswith(remote) or remote.startswith(current) or short_sha(current) == short_sha(remote)


def check_for_update() -> UpdateResult:
    current_sha = BUILD_SHA.strip() or "unknown"
    latest_release = fetch_latest_release()
    latest_tag = latest_release.get("tag_name", "").strip()
    latest_version = release_version_from_tag(latest_tag)

    if latest_version and not is_remote_version_newer(APP_RELEASE_VERSION, latest_version):
        return UpdateResult(
            current_sha=current_sha,
            remote_sha=latest_tag,
            update_available=False,
            message=f"已经是最新版本。当前: {APP_VERSION}，最新发布: {latest_tag}，打包时间: {BUILD_DATE}",
        )

    remote_sha = str(latest_release.get("target_commitish", "")).strip() or fetch_remote_sha()
    if current_sha == "unknown":
        return UpdateResult(
            current_sha=current_sha,
            remote_sha=latest_tag or remote_sha,
            update_available=False,
            message=f"当前 App 没有打包版本信息。最新发布: {latest_tag or short_sha(remote_sha)}",
        )

    if shas_match(current_sha, remote_sha):
        return UpdateResult(
            current_sha=current_sha,
            remote_sha=latest_tag or remote_sha,
            update_available=False,
            message=f"已经是最新版本。当前: {short_sha(current_sha)}，打包时间: {BUILD_DATE}",
        )

    return UpdateResult(
        current_sha=current_sha,
        remote_sha=latest_tag or remote_sha,
        update_available=True,
        message=f"发现新版本。当前: {APP_VERSION}，最新发布: {latest_tag or short_sha(remote_sha)}",
    )


def release_version_from_tag(tag_name: str) -> str | None:
    match = re.search(r"v?(\d+(?:\.\d+){1,3})(?:[-_].*)?$", tag_name.strip(), re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def is_remote_version_newer(current_version: str, remote_version: str) -> bool:
    return version_tuple(remote_version) > version_tuple(current_version)


def fetch_latest_release() -> dict[str, str]:
    errors: list[str] = []
    try:
        return fetch_latest_release_public()
    except Exception as exc:
        errors.append(f"GitHub API: {exc}")

    try:
        return fetch_latest_release_with_gh()
    except Exception as exc:
        errors.append(f"gh CLI: {exc}")

    raise RuntimeError("无法检查更新。" + "；".join(errors))


def fetch_latest_release_public() -> dict[str, str]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/latest",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ValorantHighlightClipper",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    return {
        "tag_name": str(payload.get("tag_name", "")).strip(),
        "target_commitish": str(payload.get("target_commitish", "")).strip(),
    }


def fetch_latest_release_with_gh() -> dict[str, str]:
    gh_path = find_gh()
    if not gh_path:
        raise RuntimeError("未找到 gh 命令")

    result = subprocess.run(
        [
            gh_path,
            "api",
            f"repos/{REPO}/releases/latest",
            "--jq",
            "{tag_name: .tag_name, target_commitish: .target_commitish}",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        env=github_cli_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gh api failed")
    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeError("gh response was not JSON") from exc
    return {
        "tag_name": str(payload.get("tag_name", "")).strip(),
        "target_commitish": str(payload.get("target_commitish", "")).strip(),
    }


def fetch_remote_sha() -> str:
    errors: list[str] = []
    try:
        return fetch_remote_sha_public()
    except Exception as exc:
        errors.append(f"GitHub API: {exc}")

    try:
        return fetch_remote_sha_with_gh()
    except Exception as exc:
        errors.append(f"gh CLI: {exc}")

    raise RuntimeError("无法检查更新。" + "；".join(errors))


def fetch_remote_sha_public() -> str:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/commits/{BRANCH}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ValorantHighlightClipper",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    sha = str(payload.get("sha", "")).strip()
    if not sha:
        raise RuntimeError("response missing sha")
    return sha


def fetch_remote_sha_with_gh() -> str:
    gh_path = find_gh()
    if not gh_path:
        raise RuntimeError("未找到 gh 命令")

    result = subprocess.run(
        [gh_path, "api", f"repos/{REPO}/commits/{BRANCH}", "--jq", ".sha"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
        env=github_cli_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "gh api failed")
    sha = result.stdout.strip()
    if not sha:
        raise RuntimeError("gh response missing sha")
    return sha


def find_gh() -> str | None:
    candidates = [
        shutil.which("gh"),
        "/opt/homebrew/bin/gh",
        "/usr/local/bin/gh",
        "/usr/bin/gh",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def github_cli_env() -> dict[str, str]:
    env = os.environ.copy()
    paths = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    env["PATH"] = os.pathsep.join(paths + [env.get("PATH", "")])
    return env
